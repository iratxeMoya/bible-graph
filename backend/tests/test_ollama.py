import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.ollama import (
    OllamaError,
    OllamaGenerator,
    VersePair,
    build_prompt,
    clean_phrase,
    parse_phrases,
)

PAIR = VersePair("Romanos 3:24", "Siendo justificados…", "Efesios 2:8", "Porque por gracia…")
OTHER = VersePair("Génesis 1:1", "EN el principio…", "Juan 1:1", "EN el principio era el Verbo…")


def test_build_prompt_numbers_every_pair_with_refs_and_texts():
    prompt = build_prompt([PAIR, OTHER])
    assert 'Par 1:\nA, Romanos 3:24: "Siendo justificados…"\nB, Efesios 2:8: "Porque por gracia…"' in prompt
    assert 'Par 2:\nA, Génesis 1:1: "EN el principio…"' in prompt
    assert '{"frases": [' in prompt


def test_parse_phrases_reads_the_json_list():
    raw = json.dumps({"frases": ["uno", "dos"]})
    assert parse_phrases(raw, 2) == ["uno", "dos"]


def test_parse_phrases_replaces_non_strings_with_empty_text():
    assert parse_phrases('{"frases": ["uno", 3]}', 2) == ["uno", ""]


@pytest.mark.parametrize(
    "raw",
    ["no es json", "[]", '{"otra": []}', '{"frases": "uno"}', '{"frases": ["uno"]}'],
)
def test_parse_phrases_rejects_unexpected_answers(raw):
    with pytest.raises(OllamaError):
        parse_phrases(raw, 2)


def test_clean_phrase_strips_quotes_and_extra_spaces():
    assert clean_phrase('  «La gracia   de Dios salva sin obras.»  ') == (
        "La gracia de Dios salva sin obras."
    )


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Ambos textos hablan de la protección divina.", "Hablan de la protección divina."),
        ("ambos versículos celebran el perdón de los pecados.", "Celebran el perdón de los pecados."),
        ("Ambos prometen librar la ciudad del enemigo.", "Prometen librar la ciudad del enemigo."),
        ("Ambos pasajes definen el amor de Dios.", "Definen el amor de Dios."),
        ("Ambosidad no es una palabra pero no se toca.", "Ambosidad no es una palabra pero no se toca."),
    ],
)
def test_clean_phrase_drops_a_leading_ambos(raw, clean):
    assert clean_phrase(raw) == clean


def test_clean_phrase_capitalizes_the_first_letter():
    assert clean_phrase("la salvación es un regalo de Dios.") == "La salvación es un regalo de Dios."


@pytest.mark.parametrize("text", ["", "Muy corta.", "x" * 161, '""'])
def test_clean_phrase_rejects_unreasonable_lengths(text):
    assert clean_phrase(text) is None


class FakeOllama(BaseHTTPRequestHandler):
    received: list[dict] = []
    reply: dict = {}

    def do_POST(self):  # noqa: N802
        length = int(self.headers["Content-Length"])
        FakeOllama.received.append(json.loads(self.rfile.read(length)))
        body = json.dumps(FakeOllama.reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_ollama():
    FakeOllama.received = []
    server = HTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


def test_generator_sends_one_request_and_returns_the_phrases(fake_ollama):
    FakeOllama.reply = {"response": json.dumps({"frases": ["primera frase", "segunda frase"]})}
    generator = OllamaGenerator(fake_ollama, model="gemma4:e4b")
    assert generator.generate([PAIR, OTHER]) == ["primera frase", "segunda frase"]
    [request] = FakeOllama.received
    assert request["model"] == "gemma4:e4b"
    assert request["format"] == "json"
    assert request["stream"] is False
    assert "Romanos 3:24" in request["prompt"] and "Juan 1:1" in request["prompt"]


def test_generator_raises_when_the_answer_does_not_fit(fake_ollama):
    FakeOllama.reply = {"response": json.dumps({"frases": ["solo una"]})}
    with pytest.raises(OllamaError):
        OllamaGenerator(fake_ollama).generate([PAIR, OTHER])


def test_generator_raises_when_ollama_is_unreachable():
    with pytest.raises(OllamaError):
        OllamaGenerator("http://127.0.0.1:1", timeout=2).generate([PAIR])
