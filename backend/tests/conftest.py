import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    app = create_app(Settings(database_url="", allowed_origins=["http://localhost:5173"]))
    with TestClient(app) as test_client:
        yield test_client
