from tests.conftest import auth_headers


def test_list_departments(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/knowledge", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["departments"]) == 9


def test_get_department_kb(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/knowledge/procurement", headers=headers)
    assert resp.status_code == 200
    assert "Procurement" in resp.text
