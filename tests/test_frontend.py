"""Frontend markup. Ponašanje u browseru (klik na strane, filter) provjereno je ručno."""


# Scenarij: Paginacija liste korisnika

def test_dashboard_ima_paginaciju_liste(logged_in_client):
    html = logged_in_client.get("/").text
    assert 'id="customerList"' in html
    assert 'id="customerPager"' in html
    js = logged_in_client.get("/main.js").text
    assert "const PAGE_SIZE = 10;" in js
