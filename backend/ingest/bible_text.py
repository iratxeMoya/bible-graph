"""Parseo del fichero VPL de la Reina-Valera 1909 de eBible.org."""

from collections.abc import Iterable
from dataclasses import dataclass

from ingest.books import BY_EBIBLE, verse_id

URL = "https://ebible.org/Scriptures/spaRV1909_vpl.zip"
ZIP_MEMBER = "spaRV1909_vpl.txt"
TRANSLATION = "RV1909"


@dataclass(frozen=True)
class VerseText:
    id: int
    book_id: int
    chapter: int
    verse: int
    text: str


def parse_line(line: str) -> VerseText | None:
    """Convierte 'GEN 1:1 EN el principio...' en un VerseText.

    Devuelve None si la línea está vacía o si el versículo no tiene texto: el fichero
    trae 18 referencias sin texto allí donde la numeración de RV1909 difiere de la KJV.
    """
    line = line.lstrip("﻿").strip()
    if not line:
        return None
    parts = line.split(" ", 2)
    if len(parts) < 2:
        raise ValueError(f"línea de RV1909 mal formada: {line!r}")
    code, chapter_verse = parts[0], parts[1]
    text = parts[2].strip() if len(parts) == 3 else ""
    book = BY_EBIBLE.get(code)
    if book is None:
        raise ValueError(f"código de libro desconocido {code!r} en: {line!r}")
    try:
        chapter_s, verse_s = chapter_verse.split(":")
        chapter, verse = int(chapter_s), int(verse_s)
    except ValueError:
        raise ValueError(f"referencia mal formada {chapter_verse!r} en: {line!r}") from None
    if not text:
        return None
    return VerseText(verse_id(book.id, chapter, verse), book.id, chapter, verse, text)


def parse_vpl(lines: Iterable[str]) -> list[VerseText]:
    return [v for v in map(parse_line, lines) if v is not None]
