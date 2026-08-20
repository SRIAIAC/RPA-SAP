"""Full end-to-end coverage of the 5 golden Invoice 3-Way Matching
scenarios, exercised through the real HTTP API -> WorkflowEngine ->
SAPIntegrationService -> live mock-sap -> BusinessRulesEngine chain (not
just the rules-engine unit test in test_business_rules.py).

Requires mock-sap running on port 8100 — skipped automatically otherwise.
"""

import time

import httpx
import pytest

from tests.conftest import auth_headers

SAP_URL = "http://127.0.0.1:8100"


def _sap_up() -> bool:
    try:
        return httpx.get(f"{SAP_URL}/api/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _sap_up(), reason="mock-sap is not running on port 8100"),
]


def _get_inv_match_workflow_id(client, headers) -> int:
    workflows = client.get("/api/workflows", headers=headers).json()
    inv_match = next(w for w in workflows if w["key"] == "INV_MATCH")
    return inv_match["id"]


def _run_scenario(client, headers, workflow_id: int, scenario: str) -> dict:
    resp = client.post(f"/api/runs?workflow_id={workflow_id}&scenario={scenario}", headers=headers)
    assert resp.status_code == 201
    run = resp.json()

    deadline = time.time() + 30
    final = run
    while time.time() < deadline:
        final = client.get(f"/api/runs/{run['id']}", headers=headers).json()
        if final["status"] in ("Completed", "Exception"):
            break
        time.sleep(0.5)
    return final


def test_scenario_success_auto_approves(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "success")
    assert result["status"] == "Completed"
    assert "matched" in result["result_summary"].lower()


def test_scenario_quantity_mismatch_raises_exception(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "quantity_mismatch")
    assert result["status"] == "Exception"
    assert "quantity mismatch" in result["result_summary"].lower()


def test_scenario_price_mismatch_raises_exception(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "price_mismatch")
    assert result["status"] == "Exception"
    assert "price variance" in result["result_summary"].lower()


def test_scenario_duplicate_invoice_raises_exception(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "duplicate_invoice")
    assert result["status"] == "Exception"
    assert "duplicate" in result["result_summary"].lower()


def test_scenario_missing_grn_raises_exception(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "missing_grn")
    assert result["status"] == "Exception"
    assert "grn" in result["result_summary"].lower()


def test_unresolved_scenario_falls_back_to_success(client):
    headers = auth_headers(client, "admin")
    workflow_id = _get_inv_match_workflow_id(client, headers)
    result = _run_scenario(client, headers, workflow_id, "not_a_real_scenario")
    assert result["status"] == "Completed"
