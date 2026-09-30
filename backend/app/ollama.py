"""Cliente mínimo de Ollama para redactar frases que explican relaciones entre versículos."""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

DEFAULT_MODEL = "gemma4:e4b"
TIMEOUT_SECONDS = 60
MIN_PHRASE_LENGTH = 20
MAX_PHRASE_LENGTH = 160
QUOTES = "\"'«»“”‘’"
# "Ambos textos hablan de…" no aporta nada: se deja en "Hablan de…".
BOTH_PREFIX = re.compile(r"^ambos(?:\s+(?:textos|versículos|versiculos|pasajes))?\s+", re.IGNORECASE)

PROMPT = """Varios pares de versículos de la Biblia (Reina-Valera 1909) están unidos por referencias cruzadas.

{items}

Para cada par, escribe en español actual UNA frase de 6 a 12 palabras que explique qué relación hay entre los dos versículos. Di directamente la idea que los une, sin empezar por «Ambos». No repitas las referencias. No uses comillas.
Responde solo con un objeto JSON con la forma {{"frases": ["frase del par 1", "frase del par 2", ...]}}, con una frase por par y en el mismo orden."""


@dataclass(frozen=True)
class VersePair:
    a_ref: str
    a_text: str
    b_ref: str
    b_text: str


class Generator(Protocol):
    """Redacta una frase por par. Devuelve una lista del mismo tamaño o lanza una excepción."""

    model: str

    def generate(self, pairs: list[VersePair]) -> list[str]: ...


class OllamaError(Exception):
    pass


def build_prompt(pairs: list[VersePair]) -> str:
    items = "\n\n".join(
        f'Par {n}:\nA, {p.a_ref}: "{p.a_text}"\nB, {p.b_ref}: "{p.b_text}"'
        for n, p in enumerate(pairs, start=1)
    )
    return PROMPT.format(items=items)


def parse_phrases(raw: str, expected: int) -> list[str]:
    """Extrae la lista de frases de la respuesta del modelo. Lanza OllamaError si no cuadra."""
    try:
        phrases = json.loads(raw)["frases"]
    except (ValueError, TypeError, KeyError) as error:
        raise OllamaError(f"respuesta ilegible: {raw[:200]!r}") from error
    if not isinstance(phrases, list) or len(phrases) != expected:
        raise OllamaError(f"se esperaban {expected} frases y llegaron {phrases!r}"[:300])
    return [p if isinstance(p, str) else "" for p in phrases]


def clean_phrase(text: str) -> str | None:
    """Quita comillas y espacios de los extremos. Devuelve None si la longitud no es razonable."""
    text = " ".join(text.split()).strip(QUOTES + " ")
    text = BOTH_PREFIX.sub("", text)
    text = text[:1].upper() + text[1:]
    if not MIN_PHRASE_LENGTH <= len(text) <= MAX_PHRASE_LENGTH:
        return None
    return text


class OllamaGenerator:
    def __init__(self, url: str, model: str = DEFAULT_MODEL, timeout: float = TIMEOUT_SECONDS):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, pairs: list[VersePair]) -> list[str]:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": build_prompt(pairs),
                "stream": False,
                "think": False,
                "format": "json",
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/api/generate", body, {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except (OSError, ValueError) as error:
            raise OllamaError(f"no se pudo consultar Ollama en {self.url}: {error}") from error
        return parse_phrases(data.get("response", ""), len(pairs))
