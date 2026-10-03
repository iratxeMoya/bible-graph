import asyncio

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import explanations
from app.config import Settings
from app.db import create_pool
from app.main import create_app
from tests.data import EPH_2_8, GEN_1_1, PS_32_1, ROM_3_24, TIT_3_5
from tests.fakes import FakeGenerator


@pytest.fixture(autouse=True)
def no_explanations(database_url):
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE relation_explanations")


def make_client(database_url, generator):
    settings = Settings(database_url=database_url, allowed_origins=[])
    return TestClient(create_app(settings, generator=generator))


def stored(database_url):
    with psycopg.connect(database_url) as conn:
        return conn.execute(
            "SELECT verse_a, verse_b, text, model FROM relation_explanations ORDER BY 1, 2"
        ).fetchall()


def explain(client, verse, *others):
    response = client.get(
        "/api/explanations", params={"verse": verse, "others": ",".join(map(str, others))}
    )
    assert response.status_code == 200, response.text
    return {e["other"]: e["text"] for e in response.json()["explanations"]}


def test_missing_phrases_are_generated_in_one_call_and_stored(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, EPH_2_8, TIT_3_5)
    assert texts == {
        EPH_2_8: "Frase de prueba que une Romanos 3:24 con Efesios 2:8.",
        TIT_3_5: "Frase de prueba que une Romanos 3:24 con Tito 3:5.",
    }
    assert len(generator.calls) == 1
    assert len(generator.calls[0]) == 2
    assert [row[:2] for row in stored(database_url)] == [(ROM_3_24, EPH_2_8), (ROM_3_24, TIT_3_5)]
    assert {row[3] for row in stored(database_url)} == {"modelo-falso"}


def test_stored_phrases_are_not_generated_again(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        first = explain(client, ROM_3_24, EPH_2_8)
        second = explain(client, ROM_3_24, EPH_2_8)
    assert first == second
    assert len(generator.calls) == 1


def test_a_phrase_serves_both_directions(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        explain(client, ROM_3_24, EPH_2_8)
        texts = explain(client, EPH_2_8, ROM_3_24)
    assert texts[ROM_3_24] == "Frase de prueba que une Romanos 3:24 con Efesios 2:8."
    assert len(generator.calls) == 1


def test_verses_without_a_cross_reference_get_no_phrase(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, GEN_1_1, ROM_3_24)
    assert texts == {GEN_1_1: None, ROM_3_24: None}
    assert generator.calls == []


def test_answer_keeps_the_order_of_others(database_url):
    with make_client(database_url, FakeGenerator()) as client:
        response = client.get(
            "/api/explanations",
            params={"verse": ROM_3_24, "others": f"{TIT_3_5},{GEN_1_1},{EPH_2_8}"},
        )
    assert [e["other"] for e in response.json()["explanations"]] == [TIT_3_5, GEN_1_1, EPH_2_8]


def test_invalid_phrases_are_returned_as_null_and_not_stored(database_url):
    def phrase(pair):
        return "corta" if pair.b_ref == "Salmos 32:1" or pair.a_ref == "Salmos 32:1" else (
            "Una frase suficientemente larga para ser válida."
        )

    with make_client(database_url, FakeGenerator(phrase)) as client:
        texts = explain(client, ROM_3_24, PS_32_1, EPH_2_8)
    assert texts == {PS_32_1: None, EPH_2_8: "Una frase suficientemente larga para ser válida."}
    assert [row[:2] for row in stored(database_url)] == [(ROM_3_24, EPH_2_8)]


def test_generator_failure_answers_200_with_nulls(database_url):
    generator = FakeGenerator(error=RuntimeError("Ollama no responde"))
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, EPH_2_8)
    assert texts == {EPH_2_8: None}
    assert stored(database_url) == []


def test_without_ollama_only_stored_phrases_are_returned(database_url):
    with make_client(database_url, FakeGenerator()) as client:
        explain(client, ROM_3_24, EPH_2_8)
    with make_client(database_url, None) as client:
        assert client.app.state.generator is None
        texts = explain(client, ROM_3_24, EPH_2_8, TIT_3_5)
    assert texts == {
        EPH_2_8: "Frase de prueba que une Romanos 3:24 con Efesios 2:8.",
        TIT_3_5: None,
    }


@pytest.mark.parametrize(
    "params",
    [
        {"verse": ROM_3_24},
        {"others": str(EPH_2_8)},
        {"verse": ROM_3_24, "others": ""},
        {"verse": ROM_3_24, "others": "abc"},
        {"verse": ROM_3_24, "others": "1,,2"},
        {"verse": ROM_3_24, "others": ",".join(["1001001"] * 31)},
        {"verse": ROM_3_24, "others": "0"},
        {"verse": ROM_3_24, "others": "99999999999"},
        {"verse": 0, "others": str(EPH_2_8)},
    ],
)
def test_invalid_parameters_are_rejected(database_url, params):
    with make_client(database_url, FakeGenerator()) as client:
        assert client.get("/api/explanations", params=params).status_code == 422


def test_settings_read_ollama_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", " http://host.docker.internal:11434 \n")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = Settings.from_env()
    assert settings.ollama_url == "http://host.docker.internal:11434"
    assert settings.ollama_model == "gemma4:e4b"


def test_app_uses_ollama_only_when_configured(database_url):
    with_ollama = create_app(
        Settings(database_url=database_url, allowed_origins=[], ollama_url="http://x:11434")
    )
    without = create_app(Settings(database_url=database_url, allowed_origins=[]))
    assert with_ollama.state.generator.model == "gemma4:e4b"
    assert without.state.generator is None


@pytest.fixture
def self_reference(database_url):
    """Una referencia de un versículo a sí mismo, como Mateo 5:3 → Mateo 5:3-12 en los datos reales."""
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "INSERT INTO edges (from_verse_id, to_verse_id, weight) VALUES (%s, %s, 5)",
            (ROM_3_24, ROM_3_24),
        )
    yield
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "DELETE FROM edges WHERE from_verse_id = %s AND to_verse_id = %s", (ROM_3_24, ROM_3_24)
        )


def test_self_reference_gets_no_phrase_and_does_not_break_the_others(database_url, self_reference):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, ROM_3_24, EPH_2_8)
    assert texts == {
        ROM_3_24: None,
        EPH_2_8: "Frase de prueba que une Romanos 3:24 con Efesios 2:8.",
    }
    assert [len(call) for call in generator.calls] == [1]


class FlakyGenerator(FakeGenerator):
    """Falla en la segunda llamada y funciona en las demás."""

    def generate(self, pairs):
        self.calls.append(pairs)
        if len(self.calls) == 2:
            raise RuntimeError("se cayó a mitad")
        return [f"Frase de prueba que une {p.a_ref} con {p.b_ref}." for p in pairs]


def test_phrases_are_generated_in_chunks_and_each_chunk_is_kept(database_url, monkeypatch):
    monkeypatch.setattr(explanations, "GENERATION_CHUNK", 1)
    generator = FlakyGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, EPH_2_8, TIT_3_5, PS_32_1)
    assert [len(call) for call in generator.calls] == [1, 1, 1]
    assert sum(text is not None for text in texts.values()) == 2
    assert len(stored(database_url)) == 2


def test_cancelled_request_does_not_generate(database_url):
    generator = FakeGenerator()

    async def cancelled():
        return True

    async def run():
        pool = create_pool(database_url)
        await pool.open()
        try:
            return await explanations.explain(
                pool, generator, ROM_3_24, [EPH_2_8], cancelled=cancelled
            )
        finally:
            await pool.close()

    result = asyncio.run(run())
    assert result.explanations[0].text is None
    assert generator.calls == []
