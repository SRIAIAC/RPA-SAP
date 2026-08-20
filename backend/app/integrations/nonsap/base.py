"""Non-SAP provider interfaces — one small ABC per subsystem, matching the
mock-non-sap REST API 1:1 (see mock-systems/mock-non-sap). Kept as separate
interfaces (rather than one giant NonSAPProvider) because a real deployment
would genuinely swap these independently (e.g. real SCADA/OSIsoft PI stays
mock while CRM becomes Salesforce).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class SCADAProvider(ABC):
    @abstractmethod
    def get_equipment_telemetry(self, equipment_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def list_alarms(self, **filters: Any) -> list[dict[str, Any]]: ...


class TerminalProvider(ABC):
    @abstractmethod
    def list_receipts(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def list_tank_readings(self, **filters: Any) -> list[dict[str, Any]]: ...


class WMSProvider(ABC):
    @abstractmethod
    def get_inventory(self, **filters: Any) -> list[dict[str, Any]]: ...


class CRMProvider(ABC):
    @abstractmethod
    def list_customers(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def list_orders(self, **filters: Any) -> list[dict[str, Any]]: ...


class SupplierPortalProvider(ABC):
    @abstractmethod
    def list_documents(self, vendor_id: Optional[str] = None) -> list[dict[str, Any]]: ...

    @abstractmethod
    def submit_onboarding(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class EmailProvider(ABC):
    @abstractmethod
    def list_inbox(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def send(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class LIMSProvider(ABC):
    @abstractmethod
    def list_test_results(self, **filters: Any) -> list[dict[str, Any]]: ...


class DocumentProvider(ABC):
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[dict[str, Any]]: ...
