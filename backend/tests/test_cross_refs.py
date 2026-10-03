import pytest

from ingest.cross_refs import CrossRef, parse_line, parse_ref, parse_tsv


def test_parse_ref_converts_osis_to_verse_id():
    assert parse_ref("Gen.1.1") == 1001001
    assert parse_ref("1John.1.5") == 62001005
    assert parse_ref("Ps.119.176") == 19119176


@pytest.mark.parametrize("ref", ["Gen.1", "Gen 1:1", "Tob.1.1", "Gen.a.1", ""])
def test_parse_ref_rejects_malformed_references(ref):
    with pytest.raises(ValueError):
        parse_ref(ref)


def test_parse_line_single_verse_target():
    assert parse_line("Gen.1.1\tRom.11.36\t62") == CrossRef(1001001, 45011036, None, 62)


def test_parse_line_range_target_keeps_first_verse_and_end():
    assert parse_line("Gen.1.1\tProv.8.22-Prov.8.30\t76\n") == CrossRef(
        1001001, 20008022, 20008030, 76
    )


def test_parse_line_range_across_books():
    assert parse_line("Gen.1.1\tPs.150.6-Prov.1.2\t3") == CrossRef(1001001, 19150006, 20001002, 3)


def test_parse_line_range_of_one_verse_is_not_a_range():
    assert parse_line("Gen.1.1\tRom.11.36-Rom.11.36\t5") == CrossRef(1001001, 45011036, None, 5)


def test_parse_line_negative_votes():
    ref = parse_line("Gen.1.1\tRom.11.36\t-4")
    assert ref is not None
    assert ref.weight == -4


@pytest.mark.parametrize(
    "line", ["", "\n", "From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY 2026-09-28"]
)
def test_parse_line_skips_header_and_blank_lines(line):
    assert parse_line(line) is None


@pytest.mark.parametrize("line", ["Gen.1.1\tRom.11.36", "Gen.1.1\tRom.11.36\tmuchos"])
def test_parse_line_rejects_malformed_rows(line):
    with pytest.raises(ValueError):
        parse_line(line)


def test_parse_tsv_skips_the_header():
    lines = ["From Verse\tTo Verse\tVotes\t#comment", "Gen.1.1\tRom.11.36\t62", ""]
    assert parse_tsv(lines) == [CrossRef(1001001, 45011036, None, 62)]
