"""Formato de referencias bíblicas: 'Tito 3:5', 'Tit 3:5-7'."""


def format_ref(
    book: str,
    chapter: int,
    verse: int,
    end_book: str | None = None,
    end_chapter: int | None = None,
    end_verse: int | None = None,
) -> str:
    """Formatea un versículo o un rango. `book` es el nombre o la abreviatura a mostrar."""
    start = f"{book} {chapter}:{verse}"
    if end_book is None or end_chapter is None or end_verse is None:
        return start
    if end_book != book:
        return f"{start}-{end_book} {end_chapter}:{end_verse}"
    if end_chapter != chapter:
        return f"{start}-{end_chapter}:{end_verse}"
    if end_verse != verse:
        return f"{start}-{end_verse}"
    return start
