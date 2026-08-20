"""Synthetic SAP-shaped entities for PetroNova Energy Corporation.

Not a real SAP schema — these are simplified enough to demonstrate realistic
SAP MM/FI/PM/SD/PP/EHS integration patterns without reproducing actual SAP
table structures. No SQLModel Relationship() objects, matching the main
backend's convention — callers resolve FKs with explicit queries.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class POStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"


class InvoiceStatus(str, Enum):
    PENDING = "Pending"
    POSTED = "Posted"


class NotificationStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"


class WorkOrderStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"


class SalesOrderStatus(str, Enum):
    CREATED = "Created"
    DELIVERED = "Delivered"
    BLOCKED = "Blocked"


class ProductionOrderStatus(str, Enum):
    CONFIRMED = "Confirmed"
    UNCONFIRMED = "Unconfirmed"


class HSEStatus(str, Enum):
    OPEN = "Open"
    INVESTIGATING = "Investigating"
    CLOSED = "Closed"


class ContractStatus(str, Enum):
    ACTIVE = "Active"
    EXPIRED = "Expired"
    TERMINATED = "Terminated"


# --- SAP MM -------------------------------------------------------------------
class Vendor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_code: str = Field(index=True, unique=True)
    name: str
    gstin: Optional[str] = None
    bank_account_last4: Optional[str] = None
    insurance_expiry: Optional[date] = None
    blocked: bool = Field(default=False)
    city: str = ""
    country: str = "India"
    department: str = ""  # dominant department this vendor supplies
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Material(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_code: str = Field(index=True, unique=True)
    description: str
    uom: str = "EA"
    unit_price: float = 0.0
    hazard_classification: bool = Field(default=False)
    plant: str = ""


class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="material.id", index=True)
    plant: str
    quantity_on_hand: float = 0.0
    minimum_stock: float = 0.0


class PurchaseOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    po_number: str = Field(index=True, unique=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    status: POStatus = Field(default=POStatus.OPEN)
    currency: str = "INR"
    department: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PurchaseOrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    po_id: int = Field(foreign_key="purchaseorder.id", index=True)
    line_no: int = 1
    material_id: int = Field(foreign_key="material.id", index=True)
    quantity: float = 0.0
    unit_price: float = 0.0


class GoodsReceipt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grn_number: str = Field(index=True, unique=True)
    po_id: int = Field(foreign_key="purchaseorder.id", index=True, unique=True)
    received_at: datetime = Field(default_factory=datetime.utcnow)


class GoodsReceiptItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    grn_id: int = Field(foreign_key="goodsreceipt.id", index=True)
    po_item_id: int = Field(foreign_key="purchaseorderitem.id", index=True)
    quantity_received: float = 0.0


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_number: str = Field(index=True, unique=True)
    vendor_id: Optional[int] = Field(default=None, foreign_key="vendor.id")
    customer_id: Optional[int] = Field(default=None, foreign_key="customer.id")
    title: str = ""
    effective_date: date = date.today()
    expiry_date: date = date.today()
    owner: Optional[str] = None
    status: ContractStatus = Field(default=ContractStatus.ACTIVE)


# --- SAP FI ---------------------------------------------------------------------
class Invoice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_number: str = Field(index=True, unique=True)
    vendor_id: int = Field(foreign_key="vendor.id", index=True)
    po_id: Optional[int] = Field(default=None, foreign_key="purchaseorder.id", index=True)
    invoice_date: date = date.today()
    currency: str = "INR"
    total_amount: float = 0.0
    status: InvoiceStatus = Field(default=InvoiceStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InvoiceItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(foreign_key="invoice.id", index=True)
    po_item_id: Optional[int] = Field(default=None, foreign_key="purchaseorderitem.id")
    quantity: float = 0.0
    unit_price: float = 0.0


class CostCenter(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    department: str
    budget: float = 0.0
    spent: float = 0.0


class GLAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_number: str = Field(index=True, unique=True)
    name: str
    account_type: str = "Expense"


class Expense(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    expense_number: str = Field(index=True, unique=True)
    employee_name: str
    department: str
    amount: float = 0.0
    currency: str = "INR"
    category: str = "Travel"
    expense_date: date = date.today()
    has_receipt: bool = True


# --- SAP PM -----------------------------------------------------------------------
class FunctionalLocation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    description: str
    plant: str


class Equipment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    equipment_id: str = Field(index=True, unique=True)
    description: str
    functional_location_id: Optional[int] = Field(default=None, foreign_key="functionallocation.id")
    criticality: str = "Standard"  # "Standard" | "Critical" | "Single Point of Failure"
    plant: str = ""


class MaintenanceNotification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    notification_number: str = Field(index=True, unique=True)
    equipment_id: int = Field(foreign_key="equipment.id", index=True)
    description: str
    priority: str = "Routine"
    status: NotificationStatus = Field(default=NotificationStatus.OPEN)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaintenanceOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(index=True, unique=True)
    notification_id: Optional[int] = Field(default=None, foreign_key="maintenancenotification.id")
    equipment_id: int = Field(foreign_key="equipment.id", index=True)
    priority: str = "Routine"
    status: WorkOrderStatus = Field(default=WorkOrderStatus.OPEN)
    technician: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- SAP SD -----------------------------------------------------------------------
class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(index=True, unique=True)
    name: str
    credit_limit: float = 0.0
    credit_balance: float = 0.0
    blocked: bool = Field(default=False)
    city: str = ""
    country: str = "India"


class SalesOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    so_number: str = Field(index=True, unique=True)
    customer_id: int = Field(foreign_key="customer.id", index=True)
    status: SalesOrderStatus = Field(default=SalesOrderStatus.CREATED)
    currency: str = "INR"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SalesOrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    so_id: int = Field(foreign_key="salesorder.id", index=True)
    material_id: int = Field(foreign_key="material.id", index=True)
    quantity: float = 0.0
    unit_price: float = 0.0


class Delivery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    delivery_number: str = Field(index=True, unique=True)
    so_id: int = Field(foreign_key="salesorder.id", index=True)
    shipped_at: Optional[datetime] = None
    status: str = "Pending"


# --- SAP PP -------------------------------------------------------------------------
class ProductionOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(index=True, unique=True)
    plant: str
    material_id: int = Field(foreign_key="material.id", index=True)
    planned_quantity: float = 0.0
    status: ProductionOrderStatus = Field(default=ProductionOrderStatus.UNCONFIRMED)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProductionRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    production_order_id: int = Field(foreign_key="productionorder.id", index=True)
    plant: str
    record_date: date = date.today()
    planned_quantity: float = 0.0
    actual_quantity: float = 0.0


# --- SAP EHS ----------------------------------------------------------------------
class HSEIncident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    incident_number: str = Field(index=True, unique=True)
    description: str
    severity: str = "Low"
    location: str = ""
    equipment_id: Optional[int] = Field(default=None, foreign_key="equipment.id")
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    status: HSEStatus = Field(default=HSEStatus.OPEN)
