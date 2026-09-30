"""Tabla fija de los 66 libros: códigos de OpenBible (OSIS) y de eBible, y nombres en español."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: int
    osis: str
    ebible: str
    name_es: str
    abbr_es: str
    testament: str


_ROWS = [
    ("Gen", "GEN", "Génesis", "Gn"),
    ("Exod", "EXO", "Éxodo", "Éx"),
    ("Lev", "LEV", "Levítico", "Lv"),
    ("Num", "NUM", "Números", "Nm"),
    ("Deut", "DEU", "Deuteronomio", "Dt"),
    ("Josh", "JOS", "Josué", "Jos"),
    ("Judg", "JDG", "Jueces", "Jue"),
    ("Ruth", "RUT", "Rut", "Rt"),
    ("1Sam", "1SA", "1 Samuel", "1 S"),
    ("2Sam", "2SA", "2 Samuel", "2 S"),
    ("1Kgs", "1KI", "1 Reyes", "1 R"),
    ("2Kgs", "2KI", "2 Reyes", "2 R"),
    ("1Chr", "1CH", "1 Crónicas", "1 Cr"),
    ("2Chr", "2CH", "2 Crónicas", "2 Cr"),
    ("Ezra", "EZR", "Esdras", "Esd"),
    ("Neh", "NEH", "Nehemías", "Neh"),
    ("Esth", "EST", "Ester", "Est"),
    ("Job", "JOB", "Job", "Job"),
    ("Ps", "PSA", "Salmos", "Sal"),
    ("Prov", "PRO", "Proverbios", "Pr"),
    ("Eccl", "ECC", "Eclesiastés", "Ec"),
    ("Song", "SOL", "Cantares", "Cnt"),
    ("Isa", "ISA", "Isaías", "Is"),
    ("Jer", "JER", "Jeremías", "Jer"),
    ("Lam", "LAM", "Lamentaciones", "Lm"),
    ("Ezek", "EZE", "Ezequiel", "Ez"),
    ("Dan", "DAN", "Daniel", "Dn"),
    ("Hos", "HOS", "Oseas", "Os"),
    ("Joel", "JOE", "Joel", "Jl"),
    ("Amos", "AMO", "Amós", "Am"),
    ("Obad", "OBA", "Abdías", "Abd"),
    ("Jonah", "JON", "Jonás", "Jon"),
    ("Mic", "MIC", "Miqueas", "Mi"),
    ("Nah", "NAH", "Nahúm", "Nah"),
    ("Hab", "HAB", "Habacuc", "Hab"),
    ("Zeph", "ZEP", "Sofonías", "Sof"),
    ("Hag", "HAG", "Hageo", "Hag"),
    ("Zech", "ZEC", "Zacarías", "Zac"),
    ("Mal", "MAL", "Malaquías", "Mal"),
    ("Matt", "MAT", "Mateo", "Mt"),
    ("Mark", "MAR", "Marcos", "Mr"),
    ("Luke", "LUK", "Lucas", "Lc"),
    ("John", "JOH", "Juan", "Jn"),
    ("Acts", "ACT", "Hechos", "Hch"),
    ("Rom", "ROM", "Romanos", "Ro"),
    ("1Cor", "1CO", "1 Corintios", "1 Co"),
    ("2Cor", "2CO", "2 Corintios", "2 Co"),
    ("Gal", "GAL", "Gálatas", "Gá"),
    ("Eph", "EPH", "Efesios", "Ef"),
    ("Phil", "PHI", "Filipenses", "Fil"),
    ("Col", "COL", "Colosenses", "Col"),
    ("1Thess", "1TH", "1 Tesalonicenses", "1 Ts"),
    ("2Thess", "2TH", "2 Tesalonicenses", "2 Ts"),
    ("1Tim", "1TI", "1 Timoteo", "1 Ti"),
    ("2Tim", "2TI", "2 Timoteo", "2 Ti"),
    ("Titus", "TIT", "Tito", "Tit"),
    ("Phlm", "PHM", "Filemón", "Flm"),
    ("Heb", "HEB", "Hebreos", "He"),
    ("Jas", "JAM", "Santiago", "Stg"),
    ("1Pet", "1PE", "1 Pedro", "1 P"),
    ("2Pet", "2PE", "2 Pedro", "2 P"),
    ("1John", "1JO", "1 Juan", "1 Jn"),
    ("2John", "2JO", "2 Juan", "2 Jn"),
    ("3John", "3JO", "3 Juan", "3 Jn"),
    ("Jude", "JUD", "Judas", "Jud"),
    ("Rev", "REV", "Apocalipsis", "Ap"),
]

FIRST_NT_BOOK = 40  # Mateo

BOOKS: tuple[Book, ...] = tuple(
    Book(i, osis, ebible, name, abbr, "AT" if i < FIRST_NT_BOOK else "NT")
    for i, (osis, ebible, name, abbr) in enumerate(_ROWS, start=1)
)
BY_OSIS: dict[str, Book] = {b.osis: b for b in BOOKS}
BY_EBIBLE: dict[str, Book] = {b.ebible: b for b in BOOKS}


def verse_id(book_id: int, chapter: int, verse: int) -> int:
    """ID BBCCCVVV: Juan 3:16 -> 43003016."""
    if not (1 <= book_id <= 66 and 1 <= chapter <= 999 and 1 <= verse <= 999):
        raise ValueError(f"referencia fuera de rango: {book_id} {chapter}:{verse}")
    return book_id * 1_000_000 + chapter * 1_000 + verse
