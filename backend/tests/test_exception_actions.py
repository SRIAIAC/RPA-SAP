"""Exception queue upgrade — richer detail endpoint + human-in-the-loop
actions (Approve/Reject/Retry/Escalate/Request correction), gated by
app.rules.authorization_rules on top of the existing department RBAC."""

import time

from tests.conftest import auth_headers


def _raise_price_mismatch_exception(client, headers) -> dict:
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == "INV_MATCH")
    resp = client.post(f"/api/runs?workflow_id={workflow['id']}&scenario=price_mismatch", headers=headers)
    run_id = resp.json()["id"]

    deadline = time.time() + 30
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run_id}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)
    assert final["status"] == "Exception"

    exceptions = client.get("/api/exceptions", headers=headers).json()
    return next(e for e in exceptions if e["run_id"] == run_id)


def test_exception_detail_includes_full_trace(client):
    headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, headers)

    resp = client.get(f"/api/exceptions/{exception['id']}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()

    assert detail["reason"] == exception["reason"]
    assert len(detail["steps"]) > 0
    assert any(s["name"] == "Perform 3-way match" for s in detail["steps"])
    assert len(detail["sap_calls"]) > 0
    assert detail["ai_explanation"] is not None
    assert detail["ai_explanation"]["recommendation"]
    assert "approve" in detail["available_actions"]
    assert "retry" in detail["available_actions"]


def test_manager_without_ownership_or_department_access_is_forbidden(client):
    admin_headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, admin_headers)

    # rahul.verma is a Maintenance Manager — neither owns this Procurement
    # exception's run (admin triggered it) nor has department-level
    # visibility into Procurement, so access must be forbidden outright.
    manager_headers = auth_headers(client, "rahul.verma")
    resp = client.post(f"/api/exceptions/{exception['id']}/action", json={"action": "retry"}, headers=manager_headers)
    assert resp.status_code == 403


def test_senior_manager_can_approve_department_exception(client):
    admin_headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, admin_headers)

    sm_headers = auth_headers(client, "vikram.shah")  # Procurement Senior Manager
    resp = client.post(
        f"/api/exceptions/{exception['id']}/action", json={"action": "approve", "note": "Confirmed with vendor."}, headers=sm_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "Resolved"
    assert body["resolution_note"] == "Confirmed with vendor."
    assert any(a["action"] == "approve" for a in body["actions"])


def test_retry_creates_a_new_run(client):
    headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, headers)

    runs_before = len(client.get("/api/runs", headers=headers).json())
    resp = client.post(f"/api/exceptions/{exception['id']}/action", json={"action": "retry"}, headers=headers)
    assert resp.status_code == 200
    time.sleep(1)
    runs_after = len(client.get("/api/runs", headers=headers).json())
    assert runs_after > runs_before


def test_escalate_and_request_correction_do_not_resolve(client):
    headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, headers)

    resp = client.post(f"/api/exceptions/{exception['id']}/action", json={"action": "escalate", "note": "Needs vendor call."}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Open"

    resp2 = client.post(f"/api/exceptions/{exception['id']}/action", json={"action": "request_correction"}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "Open"
    assert len(resp2.json()["actions"]) == 2


def test_unknown_action_rejected(client):
    headers = auth_headers(client, "admin")
    exception = _raise_price_mismatch_exception(client, headers)
    resp = client.post(f"/api/exceptions/{exception['id']}/action", json={"action": "not_a_real_action"}, headers=headers)
    assert resp.status_code == 400
