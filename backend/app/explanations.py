"""Frases que explican las relaciones de un versículo: se leen de la BD o se generan con Ollama."""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from psycopg_pool import AsyncConnectionPool

from app.db import query_connection
from app.ollama import Generator, VersePair, clean_phrase
from app.refs import format_ref
from app.schemas import Explanation, ExplanationsResponse
from app.search import TRANSLATION

MAX_OTHERS = 30
# Pares por llamada al modelo. Con 30 de golpe tarda casi un minuto y basta un número de
# frases equivocado para perderlas todas; en trozos, cada uno se guarda al terminar.
GENERATION_CHUNK = 8

log = logging.getLogger(__name__)

# Los `others` que forman una referencia cruzada con `verse`, en cualquier sentido. Las
# referencias de un versículo a sí mismo (Mateo 5:3 → Mateo 5:3-12) no llevan frase.
LINKED_SQL = """
SELECT DISTINCT CASE WHEN from_verse_id = %(verse)s THEN to_verse_id ELSE from_verse_id END AS other
FROM edges
WHERE ((from_verse_id = %(verse)s AND to_verse_id = ANY(%(others)s))
    OR (to_verse_id = %(verse)s AND from_verse_id = ANY(%(others)s)))
  AND from_verse_id <> to_verse_id
"""

CACHED_SQL = """
SELECT verse_a, verse_b, text
FROM relation_explanations
WHERE verse_a = ANY(%(a)s) AND verse_b = ANY(%(b)s)
"""

TEXTS_SQL = """
SELECT v.id, b.name_es, v.chapter, v.verse, vt.text
FROM verses v
JOIN books b ON b.id = v.book_id
JOIN verse_texts vt ON vt.verse_id = v.id AND vt.translation = %(translation)s
WHERE v.id = ANY(%(ids)s)
"""

INSERT_SQL = """
INSERT INTO relation_explanations (verse_a, verse_b, text, model)
VALUES (%s, %s, %s, %s)
ON CONFLICT (verse_a, verse_b) DO NOTHING
"""


def pair_key(x: int, y: int) -> tuple[int, int]:
    """La relación no tiene dirección: se guarda con el ID menor primero."""
    return (x, y) if x < y else (y, x)


def verse_pair(key: tuple[int, int], texts: dict[int, dict]) -> VersePair:
    a, b = texts[key[0]], texts[key[1]]
    return VersePair(
        a_ref=format_ref(a["name_es"], a["chapter"], a["verse"]),
        a_text=a["text"],
        b_ref=format_ref(b["name_es"], b["chapter"], b["verse"]),
        b_text=b["text"],
    )


class _NoLock:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc: object) -> None:
        return None


_NO_LOCK = _NoLock()


async def _generate(
    generator: Generator, keys: list[tuple[int, int]], texts: dict[int, dict]
) -> dict[tuple[int, int], str]:
    """Frases válidas de un trozo de pares. Si el modelo falla, un diccionario vacío."""
    try:
        raw = await asyncio.to_thread(generator.generate, [verse_pair(key, texts) for key in keys])
    except Exception as error:  # noqa: BLE001 — sin modelo, el panel muestra el versículo
        log.warning("No se pudieron generar frases: %s", error)
        return {}
    phrases = (clean_phrase(r) for r in raw)
    return {key: text for key, text in zip(keys, phrases) if text is not None}


async def explain(
    pool: AsyncConnectionPool,
    generator: Generator | None,
    verse: int,
    others: list[int],
    *,
    lock: asyncio.Semaphore | None = None,
    cancelled: Callable[[], Awaitable[bool]] | None = None,
) -> ExplanationsResponse:
    """Frases de las relaciones de `verse` con `others`.

    `lock` hace que las generaciones vayan de una en una (Ollama las atiende así de todos
    modos). `cancelled` permite saltarse la generación si quien pidió ya se ha ido: al
    navegar rápido por el panel, las peticiones abandonadas no se quedan en cola.
    """
    async with query_connection(pool) as conn:
        cur = await conn.execute(LINKED_SQL, {"verse": verse, "others": others})
        linked = {row["other"] for row in await cur.fetchall()}
        keys = {pair_key(verse, other) for other in linked}
        cur = await conn.execute(
            CACHED_SQL, {"a": [k[0] for k in keys], "b": [k[1] for k in keys]}
        )
        known = {
            (row["verse_a"], row["verse_b"]): row["text"]
            for row in await cur.fetchall()
            if (row["verse_a"], row["verse_b"]) in keys
        }
        missing = sorted(keys - known.keys())
        texts: dict[int, dict] = {}
        if missing and generator is not None:
            ids = {verse, *(other for key in missing for other in key)}
            cur = await conn.execute(TEXTS_SQL, {"translation": TRANSLATION, "ids": list(ids)})
            texts = {row["id"]: row for row in await cur.fetchall()}

    # La llamada al modelo puede tardar decenas de segundos: se hace sin conexión del pool.
    if missing and generator is not None and all(i in texts for key in missing for i in key):
        for start in range(0, len(missing), GENERATION_CHUNK):
            chunk = missing[start : start + GENERATION_CHUNK]
            async with lock or _NO_LOCK:
                if cancelled is not None and await cancelled():
                    break
                generated = await _generate(generator, chunk, texts)
            if generated:
                async with query_connection(pool) as conn:
                    async with conn.cursor() as cur:
                        await cur.executemany(
                            INSERT_SQL,
                            [(a, b, text, generator.model) for (a, b), text in generated.items()],
                        )
                known.update(generated)

    return ExplanationsResponse(
        verse=verse,
        explanations=[
            Explanation(
                other=other,
                text=known.get(pair_key(verse, other)) if other in linked else None,
            )
            for other in others
        ],
    )
