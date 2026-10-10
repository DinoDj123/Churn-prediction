import os
from pathlib import Path

import pytest

# app.py čita USE_DB pri importu, pa ga moramo postaviti prije importa.
os.environ["USE_DB"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

REPO_ROOT = Path(__file__).resolve().parent.parent

# app.py koristi relativne putanje ("data/processed/model_results.json", "frontend"),
# a StaticFiles provjerava direktorij već pri importu.
os.chdir(REPO_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

ANA = {"email": "ana@test.me", "password": "Lozinka123"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Neprijavljen klijent; svaki test dobija svoju praznu bazu korisnika."""
    monkeypatch.setenv("USE_DB", "false")
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.db"))
    monkeypatch.chdir(REPO_ROOT)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def logged_in_client(client):
    """`client` sa registrovanom i prijavljenom Anom."""
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/login", json=ANA)
    assert r.status_code == 200
    return client
