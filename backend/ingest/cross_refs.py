"""Parseo del TSV de referencias cruzadas de OpenBible.info."""

from collections.abc import Iterable
from dataclasses import dataclass

from ingest.books import BY_OSIS, verse_id

URL = "https://a.openbible.info/data/cross-references.zip"
ZIP_MEMBER = "cross_references.txt"
KIND = "openbible"


@dataclass(frozen=True)
class CrossRef:
    from_id: int
    to_id: int
    to_end_id: int | None
    weight: int


def parse_ref(ref: str) -> int:
    """Convierte 'Gen.1.1' en 1001001."""
    parts = ref.split(".")
    if len(parts) != 3:
        raise ValueError(f"referencia mal formada: {ref!r}")
    osis, chapter, verse = parts
    book = BY_OSIS.get(osis)
    if book is None:
        raise ValueError(f"libro desconocido en la referencia: {ref!r}")
    return verse_id(book.id, int(chapter), int(verse))


def parse_line(line: str) -> CrossRef | None:
    """Convierte una fila del TSV. Devuelve None para la cabecera y las líneas vacías."""
    line = line.strip()
    if not line or line.startswith("From Verse"):
        return None
    fields = line.split("\t")
    if len(fields) < 3:
        raise ValueError(f"fila de referencias mal formada: {line!r}")
    source, target, votes = fields[0], fields[1], fields[2]
    start, _, end = target.partition("-")
    to_id = parse_ref(start)
    to_end_id = parse_ref(end) if end else None
    if to_end_id == to_id:
        to_end_id = None
    return CrossRef(parse_ref(source), to_id, to_end_id, int(votes))


def parse_tsv(lines: Iterable[str]) -> list[CrossRef]:
    return [r for r in map(parse_line, lines) if r is not None]
