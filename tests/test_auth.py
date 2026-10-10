import os
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

os.environ["USE_DB"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

ANA = {"email": "ana@test.me", "password": "Lozinka123"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("USE_DB", "false")
    monkeypatch.setenv("USERS_DB_PATH", str(tmp_path / "users.db"))
    monkeypatch.chdir(ROOT)
    with TestClient(app) as c:
        yield c


# Scenarij: Nova korisnica

def test_registracija_nove_korisnice(client):
    r = client.post("/auth/register", json=ANA)
    assert r.status_code == 201
    assert r.json() == {"email": "ana@test.me"}


def test_ista_registracija_ponovo_409(client):
    client.post("/auth/register", json=ANA)
    assert client.post("/auth/register", json=ANA).status_code == 409


def test_email_bez_obzira_na_velika_slova_409(client):
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/register", json={"email": "ANA@test.me", "password": "Lozinka123"})
    assert r.status_code == 409


def test_kratka_lozinka_422_i_korisnik_se_ne_pravi(client, tmp_path):
    r = client.post("/auth/register", json={"email": "marko@test.me", "password": "abc"})
    assert r.status_code == 422
    db = tmp_path / "users.db"
    if db.exists():
        with sqlite3.connect(db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users WHERE email = 'marko@test.me'").fetchone()[0]
        assert count == 0
    # i dalje se može registrovati sa ispravnom lozinkom
    r = client.post("/auth/register", json={"email": "marko@test.me", "password": "Lozinka123"})
    assert r.status_code == 201


def test_neispravan_email_422(client):
    r = client.post("/auth/register", json={"email": "nije-email", "password": "Lozinka123"})
    assert r.status_code == 422


# Scenarij: Hash lozinke

def test_lozinka_se_cuva_kao_hash_sa_solju(client, tmp_path):
    client.post("/auth/register", json=ANA)
    client.post("/auth/register", json={"email": "marko@test.me", "password": "Lozinka123"})
    with sqlite3.connect(tmp_path / "users.db") as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY email").fetchall()
    assert len(rows) == 2
    for row in rows:
        for value in row:
            assert "Lozinka123" not in str(value)
    # ista lozinka, različita so → različit hash
    hashes = {row[-1] for row in rows}
    assert len(hashes) == 2
