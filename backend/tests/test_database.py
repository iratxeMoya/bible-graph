from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

UNREACHABLE = "postgresql://bible:bible@127.0.0.1:1/bible?connect_timeout=1"


def test_health_db_is_ok_when_the_database_answers(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_without_database_the_api_starts_and_health_db_is_503():
    app = create_app(Settings(database_url=UNREACHABLE, allowed_origins=[]))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/health/db")
        assert response.status_code == 503
        assert response.json() == {"detail": "Base de datos no disponible"}


def test_missing_database_url_fails_at_startup():
    app = create_app(Settings(database_url="", allowed_origins=[]))
    try:
        with TestClient(app):
            pass
    except RuntimeError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("la API debería negarse a arrancar sin DATABASE_URL")
