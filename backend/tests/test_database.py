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


NOT_LOADED = {"detail": "La base de datos no tiene los datos cargados"}


def test_database_without_schema_is_503_with_cors_headers(no_schema_database_url):
    settings = Settings(database_url=no_schema_database_url, allowed_origins=["https://a.pages.dev"])
    with TestClient(create_app(settings)) as client:
        origin = {"Origin": "https://a.pages.dev"}
        assert client.get("/health").status_code == 200
        for path in ("/health/db", "/api/search?q=gracia", "/api/verses/1001001"):
            response = client.get(path, headers=origin)
            assert (path, response.status_code) == (path, 503)
            assert response.json() == NOT_LOADED
            assert response.headers["access-control-allow-origin"] == "https://a.pages.dev"


def test_database_without_data_fails_the_database_health_check(no_data_database_url):
    settings = Settings(database_url=no_data_database_url, allowed_origins=[])
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/db")
        assert response.status_code == 503
        assert response.json() == NOT_LOADED


def test_unreachable_database_makes_the_api_endpoints_503(monkeypatch):
    monkeypatch.setattr("app.db.POOL_TIMEOUT_SECONDS", 1)
    app = create_app(Settings(database_url=UNREACHABLE, allowed_origins=[]))
    with TestClient(app) as client:
        for path in ("/api/search?q=gracia", "/api/verses/1001001"):
            response = client.get(path)
            assert (path, response.status_code) == (path, 503)
            assert response.json() == {"detail": "Base de datos no disponible"}
