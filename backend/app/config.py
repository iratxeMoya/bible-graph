"""Configuración de la API a partir de variables de entorno."""

import os
from dataclasses import dataclass

DEFAULT_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
        return cls(
            database_url=os.environ.get("DATABASE_URL", "").strip(),
            allowed_origins=[o.strip().rstrip("/") for o in origins.split(",") if o.strip()],
        )
