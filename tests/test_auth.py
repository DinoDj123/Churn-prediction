import sqlite3

import pytest

from tests.conftest import ANA


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


# Scenarij: Prijava i dashboard

def test_prijava_daje_httponly_sesiju(client):
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/login", json=ANA)
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert cookie.startswith("session=")
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_me_poslije_prijave(logged_in_client):
    r = logged_in_client.get("/auth/me")
    assert r.status_code == 200
    assert r.json() == {"email": "ana@test.me"}


def test_me_bez_prijave_401(client):
    assert client.get("/auth/me").status_code == 401


def test_pogresna_lozinka_401_bez_sesije(client):
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/login", json={"email": "ana@test.me", "password": "pogresna1"})
    assert r.status_code == 401
    assert "set-cookie" not in r.headers
    assert client.get("/auth/me").status_code == 401


def test_nepostojeci_email_ista_poruka_kao_pogresna_lozinka(client):
    client.post("/auth/register", json=ANA)
    wrong_pw = client.post("/auth/login", json={"email": "ana@test.me", "password": "pogresna1"})
    no_user = client.post("/auth/login", json={"email": "niko@test.me", "password": "Lozinka123"})
    assert no_user.status_code == 401
    assert "set-cookie" not in no_user.headers
    assert no_user.json() == wrong_pw.json()


def test_prijava_ne_zavisi_od_velikih_slova_u_emailu(client):
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/login", json={"email": "Ana@Test.me", "password": "Lozinka123"})
    assert r.status_code == 200


# Scenarij: Odjava

def test_odjava_brise_sesiju(logged_in_client):
    r = logged_in_client.post("/auth/logout")
    assert r.status_code == 200
    assert logged_in_client.get("/auth/me").status_code == 401


# Scenarij: Prijava i dashboard (zaštita API-ja)

PROTECTED = [
    "/dashboard/kpis",
    "/dashboard/churn-by-contract",
    "/dashboard/top-risk",
    "/customers",
    "/customers/5419-JPRRN",
]


@pytest.mark.parametrize("path", PROTECTED)
def test_api_bez_prijave_401(client, path):
    assert client.get(path).status_code == 401


def test_dashboard_poslije_prijave(client):
    assert client.get("/dashboard/kpis").status_code == 401
    client.post("/auth/register", json=ANA)
    assert client.post("/auth/login", json=ANA).status_code == 200
    r = client.get("/dashboard/kpis")
    assert r.status_code == 200
    assert r.json()["total_customers"] == 7043
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"email": "ana@test.me"}


@pytest.mark.parametrize("path", PROTECTED)
def test_api_poslije_prijave_200(logged_in_client, path):
    assert logged_in_client.get(path).status_code == 200


def test_pogresna_lozinka_ne_otvara_dashboard(client):
    client.post("/auth/register", json=ANA)
    client.post("/auth/login", json={"email": "ana@test.me", "password": "pogresna1"})
    assert client.get("/dashboard/kpis").status_code == 401


def test_odjava_zatvara_dashboard(logged_in_client):
    assert logged_in_client.get("/dashboard/kpis").status_code == 200
    assert logged_in_client.post("/auth/logout").status_code == 200
    assert logged_in_client.get("/dashboard/kpis").status_code == 401


# Scenarij: Stranica za prijavu

def test_pocetna_bez_prijave_preusmjerava_na_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    assert r.headers["location"] == "/login.html"


def test_login_stranica_dostupna_bez_prijave(client):
    r = client.get("/login.html")
    assert r.status_code == 200
    assert "Prijava" in r.text
    assert 'id="loginForm"' in r.text


def test_login_stranica_prikazuje_jednu_formu(client):
    html = client.get("/login.html").text
    assert '<section class="card" id="loginCard">' in html
    assert '<section class="card" id="registerCard" hidden>' in html
    assert 'id="showRegister"' in html
    assert 'id="showLogin"' in html


def test_staticki_fajlovi_dostupni_bez_prijave(client):
    assert client.get("/style.css").status_code == 200
    assert client.get("/main.js").status_code == 200


def test_pocetna_poslije_prijave_vraca_dashboard(logged_in_client):
    r = logged_in_client.get("/", follow_redirects=False)
    assert r.status_code == 200
    assert "Churn Analytics" in r.text
    assert "Odjava" in r.text

