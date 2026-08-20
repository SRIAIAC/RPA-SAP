"""SAPIntegrationService: the only thing workflow recipes and the business
rules engine are allowed to call for SAP data. Wraps whichever SAPProvider
is configured (today: always MockSAPProvider, since settings.sap_provider
defaults to "mock" and no other implementation exists) with timing +
IntegrationLog persistence, so every SAP call is visible on the Integration
Monitor page and traceable via correlation_id.
"""

import json
import time
from typing import Any, Callable, Optional

from sqlmodel import Session

from app.integrations.sap.base import SAPProvider
from app.integrations.sap.mock_provider import MockSAPProvider
from app.models_platform import IntegrationLog


def _summarize(value: Any, limit: int = 500) -> str:
    try:
        text = json.dumps(value, default=str)
    except TypeError:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


class SAPIntegrationService:
    def __init__(
        self,
        session: Session,
        correlation_id: str,
        workflow_run_id: Optional[int] = None,
        provider: Optional[SAPProvider] = None,
    ) -> None:
        self.session = session
        self.correlation_id = correlation_id
        self.workflow_run_id = workflow_run_id
        self.provider = provider or MockSAPProvider()

    def _call(self, system: str, endpoint: str, fn: Callable[..., Any], *args: Any) -> Any:
        started = time.perf_counter()
        try:
            result = fn(*args)
            latency_ms = (time.perf_counter() - started) * 1000
            self.session.add(
                IntegrationLog(
                    provider="sap",
                    system=system,
                    endpoint=endpoint,
                    method="POST" if args and isinstance(args[0], dict) else "GET",
                    success=True,
                    status_code=200,
                    latency_ms=latency_ms,
                    correlation_id=self.correlation_id,
                    workflow_run_id=self.workflow_run_id,
                    request_summary=_summarize(args),
                    response_summary=_summarize(result),
                )
            )
            self.session.commit()
            return result
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any provider failure is logged
            latency_ms = (time.perf_counter() - started) * 1000
            self.session.add(
                IntegrationLog(
                    provider="sap",
                    system=system,
                    endpoint=endpoint,
                    method="POST" if args and isinstance(args[0], dict) else "GET",
                    success=False,
                    latency_ms=latency_ms,
                    correlation_id=self.correlation_id,
                    workflow_run_id=self.workflow_run_id,
                    request_summary=_summarize(args),
                    error=str(exc),
                )
            )
            self.session.commit()
            raise

    # --- SAP MM -----------------------------------------------------------
    def get_vendor(self, vendor_id: str) -> Optional[dict[str, Any]]:
        return self._call("SAP MM", f"/api/mm/vendors/{vendor_id}", self.provider.get_vendor, vendor_id)

    def list_vendors(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("SAP MM", "/api/mm/vendors", lambda: self.provider.list_vendors(**filters))

    def get_material(self, material_id: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP MM", f"/api/mm/materials/{material_id}", self.provider.get_material, material_id
        )

    def get_purchase_order(self, po_number: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP MM",
            f"/api/mm/purchase-orders/{po_number}",
            self.provider.get_purchase_order,
            po_number,
        )

    def create_purchase_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "SAP MM", "/api/mm/purchase-orders", self.provider.create_purchase_order, payload
        )

    def get_goods_receipt(self, po_number: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP MM", f"/api/mm/goods-receipts/{po_number}", self.provider.get_goods_receipt, po_number
        )

    def get_inventory(self, material_id: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP MM", f"/api/mm/inventory/{material_id}", self.provider.get_inventory, material_id
        )

    def get_contract(self, contract_id: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP MM", f"/api/mm/contracts/{contract_id}", self.provider.get_contract, contract_id
        )

    def list_contracts_expiring(self, within_days: int) -> list[dict[str, Any]]:
        return self._call(
            "SAP MM",
            "/api/mm/contracts",
            self.provider.list_contracts_expiring,
            within_days,
        )

    def create_vendor(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("SAP MM", "/api/mm/vendors", self.provider.create_vendor, payload)

    # --- SAP FI -----------------------------------------------------------
    def get_invoice(self, invoice_number: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP FI", f"/api/fi/invoices/{invoice_number}", self.provider.get_invoice, invoice_number
        )

    def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("SAP FI", "/api/fi/invoices", self.provider.create_invoice, payload)

    # --- SAP PM -----------------------------------------------------------
    def get_equipment(self, equipment_id: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP PM", f"/api/pm/equipment/{equipment_id}", self.provider.get_equipment, equipment_id
        )

    def create_maintenance_notification(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "SAP PM", "/api/pm/notifications", self.provider.create_maintenance_notification, payload
        )

    def create_work_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("SAP PM", "/api/pm/work-orders", self.provider.create_work_order, payload)

    # --- SAP SD -------------------------------------------------------------
    def get_customer(self, customer_id: str) -> Optional[dict[str, Any]]:
        return self._call(
            "SAP SD", f"/api/sd/customers/{customer_id}", self.provider.get_customer, customer_id
        )

    def create_sales_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("SAP SD", "/api/sd/sales-orders", self.provider.create_sales_order, payload)

    # --- SAP PP ---------------------------------------------------------------
    def list_production_orders(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call(
            "SAP PP", "/api/pp/production-orders", lambda: self.provider.list_production_orders(**filters)
        )

    # --- SAP EHS ----------------------------------------------------------------
    def create_hse_incident(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("SAP EHS", "/api/ehs/incidents", self.provider.create_hse_incident, payload)
