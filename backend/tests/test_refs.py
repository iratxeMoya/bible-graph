from app.refs import format_ref


def test_single_verse():
    assert format_ref("Tito", 3, 5) == "Tito 3:5"


def test_range_in_the_same_chapter():
    assert format_ref("Tit", 3, 5, "Tit", 3, 7) == "Tit 3:5-7"


def test_range_across_chapters():
    assert format_ref("Tit", 2, 14, "Tit", 3, 2) == "Tit 2:14-3:2"


def test_range_across_books():
    assert format_ref("Sal", 150, 6, "Pr", 1, 2) == "Sal 150:6-Pr 1:2"


def test_range_that_ends_where_it_starts_is_a_single_verse():
    assert format_ref("Tit", 3, 5, "Tit", 3, 5) == "Tit 3:5"
