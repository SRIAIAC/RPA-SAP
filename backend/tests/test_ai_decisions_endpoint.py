import time

from tests.conftest import auth_headers


def test_ai_decisions_requires_senior_manager_or_above(client):
    headers = auth_headers(client, "farhan.ali")  # HSE Manager
    resp = client.get("/api/ai/decisions", headers=headers)
    assert resp.status_code == 403


def test_ai_decisions_lists_entries_after_a_run(client):
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

    decisions = client.get("/api/ai/decisions", params={"workflow_run_id": run_id}, headers=headers).json()
    assert len(decisions) > 0
    assert any(d["use_case"] == "invoice_extraction" for d in decisions)
