"""Dataset mínimo para los tests de la API."""

from ingest.bible_text import VerseText
from ingest.books import BY_OSIS, verse_id
from ingest.cross_refs import CrossRef


def vid(osis: str, chapter: int, verse: int) -> int:
    return verse_id(BY_OSIS[osis].id, chapter, verse)


GEN_1_1 = vid("Gen", 1, 1)
GEN_1_3 = vid("Gen", 1, 3)
PS_32_1 = vid("Ps", 32, 1)
JOHN_1_14 = vid("John", 1, 14)
JOHN_1_16 = vid("John", 1, 16)
ROM_3_24 = vid("Rom", 3, 24)
ROM_8_32 = vid("Rom", 8, 32)
EPH_2_8 = vid("Eph", 2, 8)
EPH_2_9 = vid("Eph", 2, 9)
TIT_3_5 = vid("Titus", 3, 5)
TIT_3_6 = vid("Titus", 3, 6)
TIT_3_7 = vid("Titus", 3, 7)

# "gracia" aparece en Juan 1:14, Juan 1:16 (dos veces), Romanos 3:24 y Efesios 2:8.
# El texto de Tito 3:7 está alterado a propósito para que no la contenga.
_TEXTS = {
    GEN_1_1: "EN el principio crió Dios los cielos y la tierra.",
    GEN_1_3: "Y dijo Dios: Sea la luz: y fué la luz.",
    PS_32_1: "BIENAVENTURADO aquel cuyas iniquidades son perdonadas, y borrados sus pecados.",
    JOHN_1_14: "Y aquel Verbo fué hecho carne, y habitó entre nosotros, lleno de gracia y de verdad.",
    JOHN_1_16: "Porque de su plenitud tomamos todos, y gracia por gracia.",
    ROM_3_24: "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
    ROM_8_32: "El que aun á su propio Hijo no perdonó, antes le entregó por todos nosotros.",
    EPH_2_8: "Porque por gracia sois salvos por la fe; y esto no de vosotros, pues es don de Dios:",
    EPH_2_9: "No por obras, para que nadie se gloríe.",
    TIT_3_5: "No por obras de justicia que nosotros habíamos hecho, mas por su misericordia nos salvó,",
    TIT_3_6: "El cual derramó en nosotros abundantemente por Jesucristo nuestro Salvador,",
    TIT_3_7: "Para que, justificados por su bondad, seamos hechos herederos de la vida eterna.",
}

VERSES = [
    VerseText(id_, id_ // 1_000_000, id_ // 1_000 % 1_000, id_ % 1_000, text)
    for id_, text in sorted(_TEXTS.items())
]

EDGES = [
    CrossRef(ROM_3_24, EPH_2_8, None, 40),
    CrossRef(EPH_2_8, ROM_3_24, None, 35),      # arista inversa de la anterior
    CrossRef(ROM_3_24, TIT_3_5, TIT_3_7, 30),   # destino con rango
    CrossRef(EPH_2_8, TIT_3_5, None, 15),       # arista entre dos vecinos de Romanos 3:24
    CrossRef(TIT_3_5, EPH_2_9, None, 20),       # Efesios 2:9 queda a dos saltos de Romanos 3:24
    CrossRef(GEN_1_1, JOHN_1_14, None, 50),     # arista entrante a una semilla
    CrossRef(JOHN_1_16, GEN_1_3, None, 0),      # peso 0: fuera con min_weight=1
    CrossRef(ROM_3_24, PS_32_1, None, 5),
    CrossRef(PS_32_1, ROM_8_32, None, 10),      # Romanos 8:32 queda a dos saltos
]
