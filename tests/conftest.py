import os
from pathlib import Path

import pytest

# app.py čita USE_DB pri importu, pa ga moramo postaviti prije importa.
os.environ["USE_DB"] = "false"

REPO_ROOT = Path(__file__).resolve().parent.parent

# app.py koristi relativne putanje ("data/processed/model_results.json", "frontend"),
# a StaticFiles provjerava direktorij već pri importu.
os.chdir(REPO_ROOT)

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    with TestClient(app) as c:
        yield c
