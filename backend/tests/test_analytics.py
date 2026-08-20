"""Analytics KPI endpoint — dynamic computation from real WorkflowRun data,
never hardcoded."""

import time

from tests.conftest import auth_headers


def _run_and_wait(client, headers, workflow_key: str, scenario: str | None = None) -> dict:
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == workflow_key)
    url = f"/api/runs?workflow_id={workflow['id']}"
    if scenario:
        url += f"&scenario={scenario}"
    resp = client.post(url, headers=headers)
    run = resp.json()
    deadline = time.time() + 30
    final = run
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run['id']}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)
    return final


def test_analytics_requires_senior_manager_or_above(client):
    headers = auth_headers(client, "farhan.ali")  # HSE Manager
    resp = client.get("/api/analytics/dashboard", headers=headers)
    assert resp.status_code == 403


def test_analytics_dashboard_reflects_real_runs(client):
    headers = auth_headers(client, "admin")
    _run_and_wait(client, headers, "INV_MATCH", "success")

    resp = client.get("/api/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["org"]["total_runs"] > 0
    assert len(body["departments"]) > 0
    assert len(body["workflows"]) > 0

    inv_match = next(w for w in body["workflows"] if w["workflow_key"] == "INV_MATCH")
    assert inv_match["total_runs"] > 0
    assert inv_match["avg_processing_seconds"] > 0
    assert inv_match["manual_processing_minutes"] == 15


def test_analytics_scoped_to_department_for_dept_head(client):
    headers = auth_headers(client, "neha.kapoor")  # Procurement Dept Head
    resp = client.get("/api/analytics/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    depts = {w["department"] for w in body["workflows"]}
    assert depts <= {"Procurement"}
