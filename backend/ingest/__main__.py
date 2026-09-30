"""CLI de ingesta: python -m ingest [--force-download] [--cache-dir DIR]."""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from ingest import bible_text, cross_refs
from ingest.books import BOOKS
from ingest.download import fetch, read_zip_lines
from ingest.load import apply_schema, load, resolve_edges

EXPECTED_BOOKS = 66
EXPECTED_VERSES = 31_084
MIN_EDGES = 340_000
MAX_DROPPED_SHOWN = 20


def check_counts(books: int, verses: int, edges: int) -> list[str]:
    """Devuelve los motivos por los que los datos no son los esperados (vacío si todo cuadra)."""
    problems = []
    if books != EXPECTED_BOOKS:
        problems.append(f"se esperaban {EXPECTED_BOOKS} libros y hay {books}")
    if verses != EXPECTED_VERSES:
        problems.append(f"se esperaban {EXPECTED_VERSES} versículos y hay {verses}")
    if edges < MIN_EDGES:
        problems.append(f"se esperaban al menos {MIN_EDGES} aristas y hay {edges}")
    return problems


def describe_target(database_url: str) -> str:
    """Servidor y base de datos de destino, sin credenciales, para mostrarlo antes de cargar."""
    info = conninfo_to_dict(database_url)
    return f"{info.get('host', 'localhost')}/{info.get('dbname', '')}"


def database_url_from_env() -> str | None:
    """`DATABASE_URL` sin espacios ni saltos de línea sobrantes, o None si falta o está vacía."""
    return os.environ.get("DATABASE_URL", "").strip() or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(os.environ.get("INGEST_CACHE_DIR", "data"))
    )
    args = parser.parse_args(argv)

    database_url = database_url_from_env()
    if not database_url:
        print("Falta la variable de entorno DATABASE_URL", file=sys.stderr)
        return 2
    print(f"Destino: {describe_target(database_url)}")

    print("Descargando RV1909...")
    text_zip = fetch(bible_text.URL, args.cache_dir, args.force_download)
    print("Descargando referencias cruzadas de OpenBible...")
    refs_zip = fetch(cross_refs.URL, args.cache_dir, args.force_download)

    verses = bible_text.parse_vpl(read_zip_lines(text_zip, bible_text.ZIP_MEMBER))
    refs = cross_refs.parse_tsv(read_zip_lines(refs_zip, cross_refs.ZIP_MEMBER))
    edges, dropped = resolve_edges(refs, {v.id for v in verses})
    books_with_text = len({v.book_id for v in verses})

    problems = check_counts(books_with_text, len(verses), len(edges))
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print("No se ha cargado nada.", file=sys.stderr)
        return 1

    with psycopg.connect(database_url) as conn:
        apply_schema(conn)
        load(conn, verses, edges)

    print(f"Libros:              {len(BOOKS)}")
    print(f"Versículos:          {len(verses)}")
    print(f"Aristas cargadas:    {len(edges)}")
    print(f"Aristas descartadas: {len(dropped)} (apuntan a versículos que no existen en RV1909)")
    for ref in dropped[:MAX_DROPPED_SHOWN]:
        print(f"  {ref.from_id} -> {ref.to_id}")
    if len(dropped) > MAX_DROPPED_SHOWN:
        print(f"  ... y {len(dropped) - MAX_DROPPED_SHOWN} más")
    return 0


if __name__ == "__main__":
    sys.exit(main())
