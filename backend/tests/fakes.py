"""Generador de frases falso para los tests: registra las llamadas y no usa ningún modelo."""

from collections.abc import Callable

from app.ollama import VersePair


def default_phrase(pair: VersePair) -> str:
    return f"Frase de prueba que une {pair.a_ref} con {pair.b_ref}."


class FakeGenerator:
    model = "modelo-falso"

    def __init__(
        self,
        phrase: Callable[[VersePair], str] = default_phrase,
        error: Exception | None = None,
    ):
        self.phrase = phrase
        self.error = error
        self.calls: list[list[VersePair]] = []

    def generate(self, pairs: list[VersePair]) -> list[str]:
        self.calls.append(pairs)
        if self.error is not None:
            raise self.error
        return [self.phrase(pair) for pair in pairs]
