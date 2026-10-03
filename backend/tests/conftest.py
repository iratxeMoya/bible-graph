import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import Settings
from app.main import create_app
from ingest.load import apply_schema, load
from tests.data import EDGES, VERSES

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://bible:bible@db:5432/bible_test"
)


def ensure_database(url: str, *, recreate: bool = False) -> None:
    """Crea la BD de tests si no existe. Con `recreate`, la borra antes para dejarla vacía."""
    dbname = conninfo_to_dict(url)["dbname"]
    if not dbname.endswith("_test"):
        raise RuntimeError(f"La BD de tests debe acabar en '_test' y es {dbname!r}")
    admin = make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        if recreate:
            conn.execute(f'DROP DATABASE IF EXISTS "{dbname}"')
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{dbname}"')


@pytest.fixture(scope="session")
def database_url() -> str:
    """Crea (si hace falta) la BD de tests y la carga con el dataset mínimo."""
    ensure_database(TEST_DATABASE_URL)
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        apply_schema(conn)
        load(conn, VERSES, EDGES)
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def no_schema_database_url() -> str:
    """Una BD recién creada, sin tablas: la situación antes de la primera ingesta."""
    url = make_conninfo(TEST_DATABASE_URL, dbname="bible_noschema_test")
    ensure_database(url, recreate=True)
    return url


@pytest.fixture(scope="session")
def no_data_database_url() -> str:
    """Una BD con el esquema aplicado pero sin ningún versículo."""
    url = make_conninfo(TEST_DATABASE_URL, dbname="bible_nodata_test")
    ensure_database(url, recreate=True)
    with psycopg.connect(url) as conn:
        apply_schema(conn)
    return url


@pytest.fixture
def client(database_url: str):
    app = create_app(Settings(database_url=database_url, allowed_origins=["http://localhost:5173"]))
    with TestClient(app) as test_client:
        yield test_client
