"""Carga de libros, versículos y aristas en Postgres."""

from pathlib import Path

import psycopg

from ingest.bible_text import TRANSLATION, VerseText
from ingest.books import BOOKS
from ingest.cross_refs import KIND, CrossRef

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def apply_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def resolve_edges(
    refs: list[CrossRef], verse_ids: set[int]
) -> tuple[list[CrossRef], list[CrossRef]]:
    """Separa las aristas cargables de las que apuntan a versículos inexistentes.

    Una arista se descarta si falta su origen o el primer versículo de su destino.
    Si solo falta el final del rango, se conserva como arista a un único versículo.
    """
    kept: list[CrossRef] = []
    dropped: list[CrossRef] = []
    for ref in refs:
        if ref.from_id not in verse_ids or ref.to_id not in verse_ids:
            dropped.append(ref)
        elif ref.to_end_id is not None and ref.to_end_id not in verse_ids:
            kept.append(CrossRef(ref.from_id, ref.to_id, None, ref.weight))
        else:
            kept.append(ref)
    return kept, dropped


def load(conn: psycopg.Connection, verses: list[VerseText], edges: list[CrossRef]) -> None:
    """Reemplaza todo el contenido de las cuatro tablas en una sola transacción."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("TRUNCATE edges, verse_texts, verses, books")
        with cur.copy("COPY books (id, osis, name_es, abbr_es, testament) FROM STDIN") as copy:
            for b in BOOKS:
                copy.write_row((b.id, b.osis, b.name_es, b.abbr_es, b.testament))
        with cur.copy("COPY verses (id, book_id, chapter, verse) FROM STDIN") as copy:
            for v in verses:
                copy.write_row((v.id, v.book_id, v.chapter, v.verse))
        with cur.copy("COPY verse_texts (verse_id, translation, text) FROM STDIN") as copy:
            for v in verses:
                copy.write_row((v.id, TRANSLATION, v.text))
        with cur.copy(
            "COPY edges (from_verse_id, to_verse_id, to_end_verse_id, weight, kind) FROM STDIN"
        ) as copy:
            for e in edges:
                copy.write_row((e.from_id, e.to_id, e.to_end_id, e.weight, KIND))
        cur.execute("ANALYZE books, verses, verse_texts, edges")
