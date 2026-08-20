"""SAPProvider: the abstract contract every SAP integration must satisfy.

Workflows and the business rules engine never call a provider directly —
they go through SAPIntegrationService (service.py), which wraps whichever
provider is configured (settings.sap_provider) with IntegrationLog writes.
This is what lets a future real SAP connector replace MockSAPProvider
without touching any workflow recipe.

Method surface mirrors the mock-sap REST API 1:1 (see mock-systems/mock-sap):
SAP MM (vendors, materials, purchase orders, goods receipts, inventory,
contracts), SAP FI (invoices), SAP PM (equipment, maintenance notifications/
work orders), SAP SD (customers, sales orders), SAP PP (production orders),
SAP EHS (incidents).

Future real implementations (not built now): SAPODataProvider, SAPBTPProvider,
SAPRFCProvider — each would implement this same ABC against a real SAP
system, driven by settings.sap_base_url/sap_client_id/sap_client_secret.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class SAPProvider(ABC):
    # --- SAP MM ---------------------------------------------------------
    @abstractmethod
    def get_vendor(self, vendor_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def list_vendors(self, **filters: Any) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_material(self, material_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def get_purchase_order(self, po_number: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def create_purchase_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def get_goods_receipt(self, po_number: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def get_inventory(self, material_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def get_contract(self, contract_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def list_contracts_expiring(self, within_days: int) -> list[dict[str, Any]]: ...

    @abstractmethod
    def create_vendor(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    # --- SAP FI -----------------------------------------------------------
    @abstractmethod
    def get_invoice(self, invoice_number: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def create_invoice(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    # --- SAP PM -----------------------------------------------------------
    @abstractmethod
    def get_equipment(self, equipment_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def create_maintenance_notification(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def create_work_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    # --- SAP SD -------------------------------------------------------------
    @abstractmethod
    def get_customer(self, customer_id: str) -> Optional[dict[str, Any]]: ...

    @abstractmethod
    def create_sales_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    # --- SAP PP ---------------------------------------------------------------
    @abstractmethod
    def list_production_orders(self, **filters: Any) -> list[dict[str, Any]]: ...

    # --- SAP EHS ----------------------------------------------------------------
    @abstractmethod
    def create_hse_incident(self, payload: dict[str, Any]) -> dict[str, Any]: ...
