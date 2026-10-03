import pytest

from ingest.books import BOOKS, BY_EBIBLE, BY_OSIS, verse_id


def test_there_are_66_books_with_unique_codes_and_names():
    assert len(BOOKS) == 66
    assert [b.id for b in BOOKS] == list(range(1, 67))
    for field in ("osis", "ebible", "name_es", "abbr_es"):
        assert len({getattr(b, field) for b in BOOKS}) == 66, field


def test_testament_boundary_is_between_malachi_and_matthew():
    assert BY_OSIS["Mal"].testament == "AT"
    assert BY_OSIS["Matt"].testament == "NT"
    assert sum(b.testament == "AT" for b in BOOKS) == 39


def test_ebible_codes_that_differ_from_usfm_map_to_the_right_book():
    assert BY_EBIBLE["SOL"].osis == "Song"
    assert BY_EBIBLE["EZE"].osis == "Ezek"
    assert BY_EBIBLE["JOH"].osis == "John"
    assert BY_EBIBLE["1JO"].osis == "1John"
    assert BY_EBIBLE["JAM"].name_es == "Santiago"


def test_verse_id_is_bbcccvvv():
    assert verse_id(43, 3, 16) == 43003016
    assert verse_id(1, 1, 1) == 1001001
    assert verse_id(19, 119, 176) == 19119176


@pytest.mark.parametrize("args", [(0, 1, 1), (67, 1, 1), (1, 0, 1), (1, 1, 0), (1, 1000, 1)])
def test_verse_id_rejects_out_of_range_parts(args):
    with pytest.raises(ValueError):
        verse_id(*args)
