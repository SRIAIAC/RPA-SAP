"""MockSAPProvider: talks to the standalone mock-sap FastAPI service over
HTTP. This is the only implementation of SAPProvider that exists today —
it is what makes `settings.sap_provider == "mock"` fully self-contained
(no real SAP system, no credentials).

Every call raises httpx exceptions on network failure; callers (always
SAPIntegrationService, never a workflow recipe directly) are responsible
for catching those and turning them into IntegrationLog failures / workflow
exceptions.
"""

from typing import Any, Optional

import httpx

from app.config import settings
from app.integrations.sap.base import SAPProvider


class MockSAPProvider(SAPProvider):
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0) -> None:
        self.base_url = (base_url or settings.mock_sap_base_url).rstrip("/")
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

    # --- SAP MM -----------------------------------------------------------
    def get_vendor(self, vendor_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/vendors/{vendor_id}")

    def list_vendors(self, **filters: Any) -> list[dict[str, Any]]:
        qs = "&".join(f"{k}={v}" for k, v in filters.items() if v is not None)
        suffix = f"?{qs}" if qs else ""
        return self._get(f"/api/mm/vendors{suffix}") or []

    def get_material(self, material_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/materials/{material_id}")

    def get_purchase_order(self, po_number: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/purchase-orders/{po_number}")

    def create_purchase_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/mm/purchase-orders", payload)

    def get_goods_receipt(self, po_number: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/goods-receipts/{po_number}")

    def get_inventory(self, material_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/inventory/{material_id}")

    def get_contract(self, contract_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/mm/contracts/{contract_id}")

    def list_contracts_expiring(self, within_days: int) -> list[dict[str, Any]]:
        return self._get(f"/api/mm/contracts?expiring_within_days={within_days}") or []

    def create_vendor(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/mm/vendors", payload)

    # --- SAP FI -------------------------------------------------------------
    def get_invoice(self, invoice_number: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/fi/invoices/{invoice_number}")

    def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/fi/invoices", payload)

    # --- SAP PM ---------------------------------------------------------------
    def get_equipment(self, equipment_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/pm/equipment/{equipment_id}")

    def create_maintenance_notification(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/pm/notifications", payload)

    def create_work_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/pm/work-orders", payload)

    # --- SAP SD -----------------------------------------------------------------
    def get_customer(self, customer_id: str) -> Optional[dict[str, Any]]:
        return self._get(f"/api/sd/customers/{customer_id}")

    def create_sales_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/sd/sales-orders", payload)

    # --- SAP PP -------------------------------------------------------------------
    def list_production_orders(self, **filters: Any) -> list[dict[str, Any]]:
        qs = "&".join(f"{k}={v}" for k, v in filters.items() if v is not None)
        suffix = f"?{qs}" if qs else ""
        return self._get(f"/api/pp/production-orders{suffix}") or []

    # --- SAP EHS ----------------------------------------------------------------
    def create_hse_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/ehs/incidents", payload)
