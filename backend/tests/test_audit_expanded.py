"""Expanded audit logging — login/logout, workflow lifecycle, exception
creation/resolution, and the audit-log endpoint's department-scoped
filtering across the new WorkflowRun/ExceptionItem target types."""

import time

from sqlmodel import Session, select

from app.models import AuditLog
from tests.conftest import TEST_ENGINE, auth_headers


def test_login_writes_audit_entry(client):
    auth_headers(client, "admin")
    with Session(TEST_ENGINE) as session:
        entries = session.exec(select(AuditLog).where(AuditLog.action == "auth.login")).all()
        assert len(entries) > 0
        assert entries[-1].detail is not None


def test_logout_writes_audit_entry(client):
    headers = auth_headers(client, "admin")
    resp = client.post("/api/auth/logout", headers=headers)
    assert resp.status_code == 204
    with Session(TEST_ENGINE) as session:
        entries = session.exec(select(AuditLog).where(AuditLog.action == "auth.logout")).all()
        assert len(entries) > 0


def test_workflow_execution_lifecycle_writes_audit_entries(client):
    headers = auth_headers(client, "admin")
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == "INV_MATCH")

    resp = client.post(f"/api/runs?workflow_id={workflow['id']}&scenario=success", headers=headers)
    run_id = resp.json()["id"]

    deadline = time.time() + 30
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run_id}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)

    with Session(TEST_ENGINE) as session:
        started = session.exec(
            select(AuditLog).where(AuditLog.action == "workflow.execution_started", AuditLog.target_id == run_id)
        ).all()
        completed = session.exec(
            select(AuditLog).where(AuditLog.action == "workflow.execution_completed", AuditLog.target_id == run_id)
        ).all()
        assert len(started) == 1
        assert len(completed) == 1


def test_workflow_exception_writes_audit_entries(client):
    headers = auth_headers(client, "admin")
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

    with Session(TEST_ENGINE) as session:
        failed = session.exec(
            select(AuditLog).where(AuditLog.action == "workflow.execution_failed", AuditLog.target_id == run_id)
        ).all()
        created = session.exec(select(AuditLog).where(AuditLog.action == "exception.created")).all()
        assert len(failed) == 1
        assert len(created) > 0


def test_exception_resolution_writes_audit_entry(client):
    headers = auth_headers(client, "admin")
    exceptions = client.get("/api/exceptions", headers=headers).json()
    open_exceptions = [e for e in exceptions if e["status"] == "Open"]
    assert open_exceptions, "expected at least one open exception from prior tests in this session"
    exception = open_exceptions[0]

    resp = client.post(
        f"/api/exceptions/{exception['id']}/resolve", json={"resolution_note": "Verified and corrected."}, headers=headers
    )
    assert resp.status_code == 200

    with Session(TEST_ENGINE) as session:
        entries = session.exec(
            select(AuditLog).where(AuditLog.action == "exception.resolved", AuditLog.target_id == exception["id"])
        ).all()
        assert len(entries) == 1


def test_admin_audit_log_includes_workflow_run_entries(client):
    headers = auth_headers(client, "admin")
    resp = client.get("/api/admin/audit-log", headers=headers)
    assert resp.status_code == 200
    actions = {e["action"] for e in resp.json()}
    assert "workflow.execution_started" in actions or "workflow.execution_completed" in actions
