from app.config import Settings


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_configured_origins(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in other.headers


def test_settings_from_env_cleans_the_origin_list(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.pages.dev/ , http://localhost:5173,, ")
    settings = Settings.from_env()
    assert settings.database_url == "postgresql://x"
    assert settings.allowed_origins == ["https://a.pages.dev", "http://localhost:5173"]


def test_settings_from_env_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    settings = Settings.from_env()
    assert settings.database_url == ""
    assert settings.allowed_origins == ["http://localhost:5173"]
