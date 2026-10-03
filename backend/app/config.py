"""Configuración de la API a partir de variables de entorno."""

import os
from dataclasses import dataclass

from app.ollama import DEFAULT_MODEL

DEFAULT_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]
    # Sin OLLAMA_URL la API solo lee las frases ya guardadas (así funciona en Render).
    ollama_url: str = ""
    ollama_model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
        return cls(
            database_url=os.environ.get("DATABASE_URL", "").strip(),
            allowed_origins=[o.strip().rstrip("/") for o in origins.split(",") if o.strip()],
            ollama_url=os.environ.get("OLLAMA_URL", "").strip(),
            ollama_model=os.environ.get("OLLAMA_MODEL", "").strip() or DEFAULT_MODEL,
        )
