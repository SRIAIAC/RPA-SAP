"""Live integration tests against the actual running mock-sap (port 8100)
and mock-non-sap (port 8200) services — proving SAPIntegrationService /
NonSAPIntegrationService genuinely make HTTP calls and get real golden-
scenario data back, not just that the provider classes are shaped right
(that's covered by the unreachable-service tests in test_sap_provider.py).

Skipped automatically if either service isn't running, so the fast unit
suite (`pytest -q`) never depends on them; run explicitly with
`pytest -m integration` once both `uvicorn app.main:app --port 8100` (in
mock-systems/mock-sap) and `--port 8200` (in mock-systems/mock-non-sap)
are up.
"""

import httpx
import pytest
from sqlmodel import Session, select

from app.integrations.nonsap.mock_provider import MockNonSAPProvider
from app.integrations.nonsap.service import NonSAPIntegrationService
from app.integrations.sap.mock_provider import MockSAPProvider
from app.integrations.sap.service import SAPIntegrationService
from app.models_platform import IntegrationLog
from tests.conftest import TEST_ENGINE

SAP_URL = "http://127.0.0.1:8100"
NONSAP_URL = "http://127.0.0.1:8200"


def _service_up(url: str) -> bool:
    try:
        return httpx.get(f"{url}/api/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.integration
requires_live_services = pytest.mark.skipif(
    not (_service_up(SAP_URL) and _service_up(NONSAP_URL)),
    reason="mock-sap and/or mock-non-sap are not running on 8100/8200",
)


@requires_live_services
def test_sap_integration_service_fetches_real_golden_data_and_logs_it():
    with Session(TEST_ENGINE) as session:
        service = SAPIntegrationService(
            session, correlation_id="live-corr-1", provider=MockSAPProvider(base_url=SAP_URL)
        )
        vendor = service.get_vendor("V-999001")
        assert vendor["name"] == "Deccan Valves & Fittings Pvt Ltd"

        po = service.get_purchase_order("PO-GOLDEN-01")
        assert po["items"][0]["quantity"] == 4

        grn = service.get_goods_receipt("PO-GOLDEN-01")
        assert grn["items"][0]["quantity_received"] == 4

        invoice = service.get_invoice("INV-GOLDEN-03")
        assert invoice["items"][0]["unit_price"] == 140000.0

        logs = session.exec(
            select(IntegrationLog).where(IntegrationLog.correlation_id == "live-corr-1")
        ).all()
        assert len(logs) == 4
        assert all(log.success for log in logs)
        assert all(log.provider == "sap" for log in logs)
        assert all(log.latency_ms >= 0 for log in logs)


@requires_live_services
def test_sap_integration_service_missing_grn_returns_none():
    with Session(TEST_ENGINE) as session:
        service = SAPIntegrationService(
            session, correlation_id="live-corr-2", provider=MockSAPProvider(base_url=SAP_URL)
        )
        grn = service.get_goods_receipt("PO-GOLDEN-05")
        assert grn is None


@requires_live_services
def test_nonsap_integration_service_fetches_golden_scada_and_crude_data():
    with Session(TEST_ENGINE) as session:
        service = NonSAPIntegrationService(
            session, correlation_id="live-corr-3", provider=MockNonSAPProvider(base_url=NONSAP_URL)
        )
        alarms = service.list_alarms(equipment_id="EQ-GOLDEN-PUMP-01")
        assert len(alarms) == 1
        assert alarms[0]["value"] == 12.0
        assert alarms[0]["threshold"] == 5.0

        receipts = service.list_receipts(po_number="PO-GOLDEN-CRUDE")
        tank_readings = service.list_tank_readings(po_number="PO-GOLDEN-CRUDE")
        assert receipts[0]["quantity_bbl"] == 9950.0
        assert tank_readings[0]["quantity_bbl"] == 9850.0

        logs = session.exec(
            select(IntegrationLog).where(IntegrationLog.correlation_id == "live-corr-3")
        ).all()
        assert len(logs) == 3
        assert all(log.provider == "nonsap" for log in logs)


@requires_live_services
def test_full_invoice_three_way_match_chain_against_live_mock_sap():
    """The exact chain Phase 7's INV_MATCH recipe will run: fetch PO, GRN,
    Invoice from the live mock-sap service and feed them into the rules
    engine, reproducing golden scenario 1 (auto-approve) end-to-end."""
    from app.rules.invoice_rules import evaluate_three_way_match

    with Session(TEST_ENGINE) as session:
        service = SAPIntegrationService(
            session, correlation_id="live-corr-4", provider=MockSAPProvider(base_url=SAP_URL)
        )
        po = service.get_purchase_order("PO-GOLDEN-01")
        grn = service.get_goods_receipt("PO-GOLDEN-01")
        invoice = service.get_invoice("INV-GOLDEN-01")

        po_item = po["items"][0]
        grn_item = grn["items"][0]
        invoice_item = invoice["items"][0]

        result = evaluate_three_way_match(
            po_quantity=po_item["quantity"],
            grn_quantity=grn_item["quantity_received"],
            invoice_quantity=invoice_item["quantity"],
            po_unit_price=po_item["unit_price"],
            invoice_unit_price=invoice_item["unit_price"],
            is_duplicate=False,
            grn_exists=True,
        )
        assert result.decision == "AUTO_APPROVE"
