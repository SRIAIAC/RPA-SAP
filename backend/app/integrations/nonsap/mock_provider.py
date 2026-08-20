"""MockNonSAPProvider: talks to the standalone mock-non-sap FastAPI service
over HTTP. Implements every non-SAP subsystem interface as one concrete
class since, today, they're all served by the same mock service.
"""

from typing import Any, Optional

import httpx

from app.config import settings
from app.integrations.nonsap.base import (
    CRMProvider,
    DocumentProvider,
    EmailProvider,
    LIMSProvider,
    SCADAProvider,
    SupplierPortalProvider,
    TerminalProvider,
    WMSProvider,
)


class MockNonSAPProvider(
    SCADAProvider,
    TerminalProvider,
    WMSProvider,
    CRMProvider,
    SupplierPortalProvider,
    EmailProvider,
    LIMSProvider,
    DocumentProvider,
):
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or settings.mock_non_sap_base_url).rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{self.base_url}{path}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(f"{self.base_url}{path}", json=payload)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _qs(filters: dict[str, Any]) -> str:
        pairs = "&".join(f"{k}={v}" for k, v in filters.items() if v is not None)
        return f"?{pairs}" if pairs else ""

    # --- SCADA --------------------------------------------------------------
    def get_equipment_telemetry(self, equipment_id: str) -> list[dict[str, Any]]:
        return self._get(f"/api/scada/equipment/{equipment_id}/telemetry") or []

    def list_alarms(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/scada/alarms{self._qs(filters)}") or []

    # --- Terminal -------------------------------------------------------------
    def list_receipts(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/terminal/receipts{self._qs(filters)}") or []

    def list_tank_readings(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/terminal/tank-readings{self._qs(filters)}") or []

    # --- WMS ----------------------------------------------------------------------
    def get_inventory(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/wms/inventory{self._qs(filters)}") or []

    # --- CRM ------------------------------------------------------------------------
    def list_customers(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/crm/customers{self._qs(filters)}") or []

    def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/crm/orders{self._qs(filters)}") or []

    # --- Supplier Portal ---------------------------------------------------------------
    def list_documents(self, vendor_id: Optional[str] = None) -> list[dict[str, Any]]:
        suffix = self._qs({"vendor_id": vendor_id}) if vendor_id else ""
        return self._get(f"/api/supplier/documents{suffix}") or []

    def submit_onboarding(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/supplier/onboarding", payload)

    # --- Email ------------------------------------------------------------------------
    def list_inbox(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/email/inbox{self._qs(filters)}") or []

    def send(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/email/send", payload)

    # --- LIMS -------------------------------------------------------------------------
    def list_test_results(self, **filters: Any) -> list[dict[str, Any]]:
        return self._get(f"/api/lims/test-results{self._qs(filters)}") or []

    # --- Document Repository -----------------------------------------------------------
    def get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/documents/{document_id}")
