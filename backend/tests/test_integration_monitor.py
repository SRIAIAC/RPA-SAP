"""Integration Monitor — per-system health + aggregated IntegrationLog stats."""

import time

from tests.conftest import auth_headers


def test_integration_status_requires_senior_manager_or_above(client):
    headers = auth_headers(client, "farhan.ali")  # HSE Manager
    resp = client.get("/api/integrations/status", headers=headers)
    assert resp.status_code == 403


def test_integration_status_reports_service_health(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/integrations/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "Mock SAP" in body["services"]
    assert "Mock Non-SAP" in body["services"]
    assert body["services"]["Mock SAP"]["status"] in ("HEALTHY", "DEGRADED", "DOWN")


def test_integration_status_aggregates_calls_after_a_run(client):
    headers = auth_headers(client, "admin")
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == "INV_MATCH")
    resp = client.post(f"/api/runs?workflow_id={workflow['id']}&scenario=success", headers=headers)
    run_id = resp.json()["id"]

    deadline = time.time() + 30
    while time.time() < deadline:
        if client.get(f"/api/runs/{run_id}", headers=headers).json()["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)

    status = client.get("/api/integrations/status", headers=headers).json()
    sap_entries = [i for i in status["integrations"] if i["provider"] == "sap"]
    assert len(sap_entries) > 0
    assert any(e["requests"] > 0 and e["successes"] > 0 for e in sap_entries)

    logs = client.get("/api/integrations/logs", params={"provider": "sap"}, headers=headers).json()
    assert len(logs) > 0
