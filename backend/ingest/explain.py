"""Pregenera frases de relación, de las referencias más votadas a las menos.

python -m ingest.explain [--limit N] [--batch B]

Se puede interrumpir con Ctrl+C y volver a lanzar: salta los pares que ya tienen frase.
"""

import argparse
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from app.explanations import INSERT_SQL, TEXTS_SQL, verse_pair
from app.ollama import DEFAULT_MODEL, Generator, OllamaGenerator, clean_phrase
from app.search import TRANSLATION
from ingest.__main__ import database_url_from_env, describe_target

# Pares sin dirección, con el mayor peso de los dos sentidos, que aún no tienen frase.
PENDING_SQL = """
SELECT p.verse_a, p.verse_b
FROM (
  SELECT least(from_verse_id, to_verse_id) AS verse_a,
         greatest(from_verse_id, to_verse_id) AS verse_b,
         max(weight) AS weight
  FROM edges
  WHERE from_verse_id <> to_verse_id
  GROUP BY 1, 2
) p
LEFT JOIN relation_explanations r ON r.verse_a = p.verse_a AND r.verse_b = p.verse_b
WHERE r.verse_a IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM unnest(%(skip_a)s::integer[], %(skip_b)s::integer[]) AS s(verse_a, verse_b)
    WHERE s.verse_a = p.verse_a AND s.verse_b = p.verse_b
  )
ORDER BY p.weight DESC, p.verse_a, p.verse_b
LIMIT %(limit)s
"""


MAX_FAILED_BATCHES = 3


@dataclass
class Progress:
    generated: int = 0
    discarded: int = 0
    # True si se paró porque el modelo falló MAX_FAILED_BATCHES lotes seguidos.
    stopped: bool = False


def pending(conn: psycopg.Connection, skip: set[tuple[int, int]], limit: int) -> list[tuple[int, int]]:
    params = {"skip_a": [k[0] for k in skip], "skip_b": [k[1] for k in skip], "limit": limit}
    rows = conn.execute(PENDING_SQL, params).fetchall()
    return [(row["verse_a"], row["verse_b"]) for row in rows]


def run(
    conn: psycopg.Connection,
    generator: Generator,
    limit: int,
    batch: int,
    report: Callable[[Progress], None] = lambda progress: None,
) -> Progress:
    """Genera hasta `limit` frases. Los pares descartados no se reintentan en esta ejecución."""
    progress = Progress()
    skip: set[tuple[int, int]] = set()
    failed_in_a_row = 0
    while progress.generated < limit:
        keys = pending(conn, skip, min(batch, limit - progress.generated))
        if not keys:
            break
        ids = list({i for key in keys for i in key})
        texts = {
            row["id"]: row
            for row in conn.execute(TEXTS_SQL, {"translation": TRANSLATION, "ids": ids})
        }
        try:
            raw = generator.generate([verse_pair(key, texts) for key in keys])
            failed_in_a_row = 0
        except Exception as error:  # noqa: BLE001
            print(f"Lote descartado: {error}", file=sys.stderr)
            raw = [""] * len(keys)
            failed_in_a_row += 1
        rows = []
        for key, text in zip(keys, (clean_phrase(r) for r in raw)):
            if text is None:
                skip.add(key)
                progress.discarded += 1
            else:
                rows.append((*key, text, generator.model))
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()
        progress.generated += len(rows)
        report(progress)
        if failed_in_a_row >= MAX_FAILED_BATCHES:
            progress.stopped = True
            break
    return progress


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest.explain")
    parser.add_argument("--limit", type=int, default=1000, help="frases a generar (1000)")
    parser.add_argument("--batch", type=int, default=8, help="pares por llamada al modelo (8)")
    args = parser.parse_args(argv)

    database_url = database_url_from_env()
    if not database_url:
        print("Falta la variable de entorno DATABASE_URL", file=sys.stderr)
        return 2
    ollama_url = os.environ.get("OLLAMA_URL", "").strip()
    if not ollama_url:
        print("Falta la variable de entorno OLLAMA_URL", file=sys.stderr)
        return 2
    model = os.environ.get("OLLAMA_MODEL", "").strip() or DEFAULT_MODEL
    generator = OllamaGenerator(ollama_url, model)
    print(f"Destino: {describe_target(database_url)} · modelo {model} en {ollama_url}")

    started = time.monotonic()

    def report(progress: Progress) -> None:
        hours = max(time.monotonic() - started, 1) / 3600
        print(
            f"Generadas {progress.generated} · descartadas {progress.discarded}"
            f" · {progress.generated / hours:.0f} frases/hora",
            flush=True,
        )

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        try:
            progress = run(conn, generator, args.limit, args.batch, report)
        except KeyboardInterrupt:
            print("Interrumpido. Lo generado hasta ahora queda guardado.")
            return 130
    if progress.stopped:
        print(
            f"Ollama no responde en {ollama_url} ({MAX_FAILED_BATCHES} lotes seguidos fallidos)."
            " ¿Está en marcha y con el modelo descargado?",
            file=sys.stderr,
        )
        return 1
    print(f"Terminado: {progress.generated} frases nuevas, {progress.discarded} descartadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
