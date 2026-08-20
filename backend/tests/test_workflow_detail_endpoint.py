from tests.conftest import auth_headers


def test_workflow_detail_returns_full_metadata(client):
    headers = auth_headers(client, "admin")
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == "INV_MATCH")

    resp = client.get(f"/api/workflows/{workflow['id']}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["key"] == "INV_MATCH"
    assert len(body["steps"]) > 0
    assert len(body["exception_reasons"]) > 0
    assert "recent_runs" in body


def test_workflow_detail_404_outside_visibility(client):
    headers = auth_headers(client, "farhan.ali")  # HSE Manager
    workflows = client.get("/api/workflows", headers=auth_headers(client, "admin")).json()
    procurement_wf = next(w for w in workflows if w["key"] == "INV_MATCH")
    resp = client.get(f"/api/workflows/{procurement_wf['id']}", headers=headers)
    assert resp.status_code == 404
