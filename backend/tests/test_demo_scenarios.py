"""Demo Scenarios — catalog + triggering through the real workflow engine
(same path as a normal Dashboard "Run now")."""

import time

from tests.conftest import auth_headers


def test_list_scenarios_requires_senior_manager_or_above(client):
    headers = auth_headers(client, "farhan.ali")  # HSE Manager
    resp = client.get("/api/demo/scenarios", headers=headers)
    assert resp.status_code == 403


def test_list_scenarios_returns_catalog(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/demo/scenarios", headers=headers)
    assert resp.status_code == 200
    scenarios = resp.json()
    assert len(scenarios) >= 10
    categories = {s["category"] for s in scenarios}
    assert {"Invoice", "Maintenance", "Vendor", "Crude", "HSE", "Production", "Contract"} <= categories


def test_run_invoice_success_scenario_reproduces_golden_outcome(client):
    headers = auth_headers(client, "admin")
    resp = client.post("/api/demo/scenarios/invoice_success/run", headers=headers)
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    deadline = time.time() + 30
    final = {}
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run_id}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)
    assert final["status"] == "Completed"


def test_run_unknown_scenario_404s(client):
    headers = auth_headers(client, "admin")
    resp = client.post("/api/demo/scenarios/not-a-real-scenario/run", headers=headers)
    assert resp.status_code == 404
