import psycopg

from ingest.cross_refs import CrossRef
from ingest.load import apply_schema, load, resolve_edges
from tests.data import EDGES, ROM_3_24, TIT_3_5, TIT_3_7, VERSES

KNOWN = {1001001, 1001002, 1001003}


def test_resolve_edges_keeps_edges_between_known_verses():
    edge = CrossRef(1001001, 1001002, 1001003, 7)
    assert resolve_edges([edge], KNOWN) == ([edge], [])


def test_resolve_edges_drops_edges_with_unknown_source_or_target():
    unknown_source = CrossRef(9, 1001001, None, 1)
    unknown_target = CrossRef(1001001, 9, None, 1)
    kept, dropped = resolve_edges([unknown_source, unknown_target], KNOWN)
    assert kept == []
    assert dropped == [unknown_source, unknown_target]


def test_resolve_edges_keeps_edge_but_clears_unknown_range_end():
    kept, dropped = resolve_edges([CrossRef(1001001, 1001002, 9, 7)], KNOWN)
    assert kept == [CrossRef(1001001, 1001002, None, 7)]
    assert dropped == []


def test_apply_schema_and_load_are_idempotent(database_url):
    with psycopg.connect(database_url) as conn:
        for _ in range(2):
            apply_schema(conn)
            load(conn, VERSES, EDGES)
        counts = conn.execute(
            "SELECT (SELECT count(*) FROM books), (SELECT count(*) FROM verses),"
            " (SELECT count(*) FROM verse_texts), (SELECT count(*) FROM edges)"
        ).fetchone()
        assert counts == (66, len(VERSES), len(VERSES), len(EDGES))
        range_end = conn.execute(
            "SELECT to_end_verse_id FROM edges WHERE from_verse_id = %s AND to_verse_id = %s",
            (ROM_3_24, TIT_3_5),
        ).fetchone()
        assert range_end == (TIT_3_7,)


def test_load_rolls_back_everything_when_it_fails(database_url):
    broken = [*EDGES, CrossRef(ROM_3_24, 99, None, 1)]  # 99 no existe: viola la clave foránea
    with psycopg.connect(database_url) as conn:
        try:
            load(conn, VERSES[:2], broken)
        except psycopg.Error:
            conn.rollback()
        else:
            raise AssertionError("load debería haber fallado")
        assert conn.execute("SELECT count(*) FROM verses").fetchone() == (len(VERSES),)
        assert conn.execute("SELECT count(*) FROM edges").fetchone() == (len(EDGES),)
