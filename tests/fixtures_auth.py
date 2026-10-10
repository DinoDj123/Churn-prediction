import pytest

ANA = {"email": "ana@test.me", "password": "Lozinka123"}


@pytest.fixture
def logged_in_client(client):
    """`client` sa registrovanom i prijavljenom Anom. Koristi: `from tests.fixtures_auth import logged_in_client`."""
    client.post("/auth/register", json=ANA)
    r = client.post("/auth/login", json=ANA)
    assert r.status_code == 200
    return client
