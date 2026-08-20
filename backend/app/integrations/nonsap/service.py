"""NonSAPIntegrationService: the only thing workflow recipes should call for
SCADA/Terminal/WMS/CRM/Supplier Portal/Email/LIMS/Document data. Same
IntegrationLog-wrapping pattern as SAPIntegrationService.
"""

import json
import time
from typing import Any, Callable, Optional

from sqlmodel import Session

from app.integrations.nonsap.mock_provider import MockNonSAPProvider
from app.models_platform import IntegrationLog


def _summarize(value: Any, limit: int = 500) -> str:
    try:
        text = json.dumps(value, default=str)
    except TypeError:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


class NonSAPIntegrationService:
    def __init__(
        self,
        session: Session,
        correlation_id: str,
        workflow_run_id: Optional[int] = None,
        provider: Optional[MockNonSAPProvider] = None,
    ) -> None:
        self.session = session
        self.correlation_id = correlation_id
        self.workflow_run_id = workflow_run_id
        self.provider = provider or MockNonSAPProvider()

    def _call(self, system: str, endpoint: str, fn: Callable[..., Any], *args: Any) -> Any:
        started = time.perf_counter()
        try:
            result = fn(*args)
            latency_ms = (time.perf_counter() - started) * 1000
            self.session.add(
                IntegrationLog(
                    provider="nonsap",
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
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000
            self.session.add(
                IntegrationLog(
                    provider="nonsap",
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

    # --- SCADA ----------------------------------------------------------------
    def get_equipment_telemetry(self, equipment_id: str) -> list[dict[str, Any]]:
        return self._call(
            "SCADA",
            f"/api/scada/equipment/{equipment_id}/telemetry",
            self.provider.get_equipment_telemetry,
            equipment_id,
        )

    def list_alarms(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("SCADA", "/api/scada/alarms", lambda: self.provider.list_alarms(**filters))

    # --- Terminal -----------------------------------------------------------------
    def list_receipts(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call(
            "Terminal Management", "/api/terminal/receipts", lambda: self.provider.list_receipts(**filters)
        )

    def list_tank_readings(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call(
            "Terminal Management",
            "/api/terminal/tank-readings",
            lambda: self.provider.list_tank_readings(**filters),
        )

    # --- WMS ------------------------------------------------------------------------
    def get_inventory(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("WMS", "/api/wms/inventory", lambda: self.provider.get_inventory(**filters))

    # --- CRM --------------------------------------------------------------------------
    def list_customers(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("CRM", "/api/crm/customers", lambda: self.provider.list_customers(**filters))

    def list_orders(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("CRM", "/api/crm/orders", lambda: self.provider.list_orders(**filters))

    # --- Supplier Portal -------------------------------------------------------------------
    def list_documents(self, vendor_id: Optional[str] = None) -> list[dict[str, Any]]:
        return self._call(
            "Supplier Portal", "/api/supplier/documents", self.provider.list_documents, vendor_id
        )

    def submit_onboarding(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "Supplier Portal", "/api/supplier/onboarding", self.provider.submit_onboarding, payload
        )

    # --- Email -----------------------------------------------------------------------------
    def list_inbox(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call("Email", "/api/email/inbox", lambda: self.provider.list_inbox(**filters))

    def send_email(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("Email", "/api/email/send", self.provider.send, payload)

    # --- LIMS ------------------------------------------------------------------------------
    def list_test_results(self, **filters: Any) -> list[dict[str, Any]]:
        return self._call(
            "LIMS", "/api/lims/test-results", lambda: self.provider.list_test_results(**filters)
        )

    # --- Document Repository ------------------------------------------------------------------
    def get_document(self, document_id: str) -> Optional[dict[str, Any]]:
        return self._call("Document Repository", f"/api/documents/{document_id}", self.provider.get_document, document_id)
