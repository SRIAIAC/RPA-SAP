"""Full-stack (HTTP API -> WorkflowEngine -> SAPIntegrationService/
NonSAPIntegrationService -> live mock services -> BusinessRulesEngine ->
Database -> Audit) coverage for the remaining golden scenarios not already
covered by test_workflow_engine_invoice.py / test_workflow_engine_maintenance.py:
Crude Reconciliation, HSE classification, Contract Expiry, Production
anomaly. Requires mock-sap (8100) and mock-non-sap (8200) running.
"""

import time

import httpx
import pytest

from tests.conftest import auth_headers

SAP_URL = "http://127.0.0.1:8100"
NONSAP_URL = "http://127.0.0.1:8200"


def _up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not (_up(SAP_URL) and _up(NONSAP_URL)), reason="mock-sap and/or mock-non-sap not running"),
]


def _run_workflow(client, headers, workflow_key: str, scenario: str | None = None) -> dict:
    workflows = client.get("/api/workflows", headers=headers).json()
    workflow = next(w for w in workflows if w["key"] == workflow_key)
    url = f"/api/runs?workflow_id={workflow['id']}"
    if scenario:
        url += f"&scenario={scenario}"
    resp = client.post(url, headers=headers)
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    deadline = time.time() + 30
    final = {}
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run_id}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)
    return final


def test_crude_reconciliation_golden_scenario_raises_hard_exception(client):
    headers = auth_headers(client, "admin")
    result = _run_workflow(client, headers, "CRUDE_RECON")
    assert result["status"] == "Exception"
    assert "variance" in result["result_summary"].lower()
    log_steps = {entry["step"] for entry in result["log"]}
    assert "Retrieve shipment quantity from Terminal System" in log_steps
    assert "Apply reconciliation rules engine" in log_steps


def test_hse_incident_critical_scenario_auto_escalates(client):
    headers = auth_headers(client, "admin")
    result = _run_workflow(client, headers, "HSE_INCIDENT", "critical")
    assert result["status"] == "Exception"
    assert "escalate" in result["result_summary"].lower()


def test_hse_incident_routine_scenario_completes(client):
    headers = auth_headers(client, "admin")
    result = _run_workflow(client, headers, "HSE_INCIDENT", "low")
    assert result["status"] == "Completed"
    assert "logged" in result["result_summary"].lower()


def test_contract_expiry_golden_scenario_flags_renewal(client):
    headers = auth_headers(client, "admin")
    result = _run_workflow(client, headers, "CONTRACT_EXPIRY")
    assert result["status"] == "Completed"
    assert "renewal" in result["result_summary"].lower()


def test_production_report_golden_scenario_raises_critical_anomaly(client):
    headers = auth_headers(client, "admin")
    result = _run_workflow(client, headers, "PROD_REPORT")
    assert result["status"] == "Exception"
    assert "variance exceeds threshold" in result["result_summary"].lower() or "variance" in result["result_summary"].lower()
