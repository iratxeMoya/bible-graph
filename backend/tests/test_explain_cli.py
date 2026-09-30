import psycopg
import pytest
from psycopg.rows import dict_row

from ingest.explain import main, run
from tests.data import EPH_2_8, GEN_1_1, JOHN_1_14, ROM_3_24
from tests.fakes import FakeGenerator


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        connection.execute("TRUNCATE relation_explanations")
        connection.commit()
        yield connection
        connection.execute("TRUNCATE relation_explanations")
        connection.commit()


def stored_pairs(conn):
    rows = conn.execute("SELECT verse_a, verse_b FROM relation_explanations ORDER BY 1, 2")
    return [(row["verse_a"], row["verse_b"]) for row in rows]


def test_run_generates_the_most_voted_pairs_first(conn):
    progress = run(conn, FakeGenerator(), limit=2, batch=8)
    # Génesis 1:1 - Juan 1:14 (50 votos) y Romanos 3:24 - Efesios 2:8 (40 en un sentido).
    assert progress.generated == 2
    assert stored_pairs(conn) == [(GEN_1_1, JOHN_1_14), (ROM_3_24, EPH_2_8)]


def test_run_respects_the_limit_across_batches(conn):
    generator = FakeGenerator()
    progress = run(conn, generator, limit=5, batch=2)
    assert progress.generated == 5
    assert [len(call) for call in generator.calls] == [2, 2, 1]


def test_run_skips_pairs_that_already_have_a_phrase(conn):
    run(conn, FakeGenerator(), limit=2, batch=8)
    generator = FakeGenerator()
    run(conn, generator, limit=1, batch=8)
    [[pair]] = generator.calls
    assert (pair.a_ref, pair.b_ref) != ("Génesis 1:1", "Juan 1:14")
    assert len(stored_pairs(conn)) == 3


def test_run_stops_when_every_pair_is_done(conn):
    # El dataset de tests tiene 8 pares sin dirección con peso >= 0.
    progress = run(conn, FakeGenerator(), limit=100, batch=3)
    assert progress.generated == 8
    assert len(stored_pairs(conn)) == 8


def test_run_discards_invalid_phrases_without_retrying_them(conn):
    generator = FakeGenerator(phrase=lambda pair: "corta")
    progress = run(conn, generator, limit=100, batch=4)
    assert progress.generated == 0
    assert progress.discarded == 8
    assert len(generator.calls) == 2
    assert stored_pairs(conn) == []


def test_run_survives_a_failing_batch(conn):
    progress = run(conn, FakeGenerator(error=RuntimeError("caído")), limit=4, batch=4)
    assert (progress.generated, progress.discarded) == (0, 8)


def test_main_needs_ollama_url(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    assert main([]) == 2
    assert "OLLAMA_URL" in capsys.readouterr().err


def test_main_needs_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err


def test_run_stops_after_three_failed_batches_in_a_row(conn):
    generator = FakeGenerator(error=RuntimeError("Ollama apagado"))
    progress = run(conn, generator, limit=100, batch=1)
    assert len(generator.calls) == 3
    assert progress.stopped is True
    assert (progress.generated, progress.discarded) == (0, 3)


def test_main_fails_when_ollama_does_not_answer(conn, database_url, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:1")
    assert main(["--limit", "5", "--batch", "1"]) == 1
    assert "Ollama no responde" in capsys.readouterr().err
