import pytest

from ingest.bible_text import VerseText, parse_line, parse_vpl


def test_parse_line_reads_book_chapter_verse_and_text():
    assert parse_line("GEN 1:1 EN el principio crió Dios los cielos y la tierra.") == VerseText(
        1001001, 1, 1, 1, "EN el principio crió Dios los cielos y la tierra."
    )


def test_parse_line_strips_bom_and_newline():
    verse = parse_line("﻿GEN 1:1 EN el principio\r\n")
    assert verse is not None
    assert verse.id == 1001001
    assert verse.text == "EN el principio"


def test_parse_line_uses_ebible_book_codes():
    verse = parse_line("JOH 3:16 Porque de tal manera amó Dios al mundo")
    assert verse is not None
    assert verse.id == 43003016


def test_parse_line_keeps_spaces_inside_the_text():
    verse = parse_line("PSA 23:1 JEHOVÁ es mi pastor; nada me faltará.")
    assert verse is not None
    assert verse.text == "JEHOVÁ es mi pastor; nada me faltará."


@pytest.mark.parametrize("line", ["", "   ", "\n", "NUM 12:16", "NUM 12:16 ", "NUM 12:16   \n"])
def test_parse_line_skips_blank_lines_and_verses_without_text(line):
    assert parse_line(line) is None


@pytest.mark.parametrize("line", ["XXX 1:1 texto", "GEN 1-1 texto", "GEN uno:1 texto", "GEN"])
def test_parse_line_rejects_malformed_lines(line):
    with pytest.raises(ValueError):
        parse_line(line)


def test_parse_vpl_returns_only_verses_with_text():
    lines = ["﻿GEN 1:1 EN el principio", "NUM 12:16 ", "", "REV 22:21 La gracia sea con todos. Amén."]
    assert [v.id for v in parse_vpl(lines)] == [1001001, 66022021]
