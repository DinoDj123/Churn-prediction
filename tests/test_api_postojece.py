"""Karakterizacioni testovi: pinuju TRENUTNO ponašanje API-ja sa USE_DB=false."""


def test_kpis(client):
    r = client.get("/dashboard/kpis")
    assert r.status_code == 200
    body = r.json()
    assert body["total_customers"] == 7043
    assert body["at_risk_customers"] == 546


def test_top_risk_limit_1(client):
    r = client.get("/dashboard/top-risk", params={"limit": 1})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["customerID"] == "5419-JPRRN"


def test_top_risk_limit_10_sortirano(client):
    r = client.get("/dashboard/top-risk", params={"limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 10
    losses = [c["expected_loss"] for c in body]
    assert losses == sorted(losses, reverse=True)


def test_churn_by_contract(client):
    r = client.get("/dashboard/churn-by-contract")
    assert r.status_code == 200
    contracts = {row["contract"] for row in r.json()}
    assert contracts == {"Month-to-month", "One year", "Two year"}
    assert len(r.json()) == 3


def test_customers_min_risk(client):
    r = client.get("/customers", params={"min_risk": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body
    assert len(body) <= 100
    assert all(c["risk"] >= 0.9 for c in body)


def test_customers_filter_contract(client):
    r = client.get("/customers?contract=Two%20year")
    assert r.status_code == 200
    body = r.json()
    assert body
    assert all(c["contract"] == "Two year" for c in body)


def test_customer_detalj(client):
    r = client.get("/customers/5419-JPRRN")
    assert r.status_code == 200
    body = r.json()
    assert body["customerID"] == "5419-JPRRN"
    assert body["risk"] == 0.9214
    assert body["best_action"] == "Godišnji ugovor"


def test_customer_nepostoji(client):
    # Pinuje trenutno (vjerovatno pogrešno) ponašanje: nepostojeći klijent daje 200
    # sa tijelom {"error": "not found"} umjesto 404.
    r = client.get("/customers/NEPOSTOJI")
    assert r.status_code == 200
    assert r.json() == {"error": "not found"}
