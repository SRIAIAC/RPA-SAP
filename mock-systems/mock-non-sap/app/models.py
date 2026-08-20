"""Synthetic non-SAP systems for PetroNova Energy Corporation: SCADA,
Terminal/Tank Farm, WMS, CRM, Supplier Portal, Email, LIMS, Document
Repository. Entities reference mock-sap records by their string business
keys (equipment_id, vendor_code, material_code, po_number) rather than
foreign keys, since these are genuinely separate services/databases in
this architecture — exactly like a real non-SAP system would only know
the SAP business key, not its internal row id.
"""

from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# --- SCADA --------------------------------------------------------------------
class SCADATelemetry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    equipment_id: str = Field(index=True)
    parameter: str  # "vibration" | "temperature" | "pressure" | "flow_rate" | "rpm"
    value: float
    unit: str = ""
    recorded_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SCADAAlarm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    equipment_id: str = Field(index=True)
    parameter: str
    value: float
    threshold: float
    severity: str = "warning"  # "critical" | "warning" | "info"
    raised_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    acknowledged: bool = Field(default=False)


# --- Terminal / Tank Farm ----------------------------------------------------------
class TerminalReceipt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    receipt_number: str = Field(index=True, unique=True)
    terminal: str
    vessel_or_source: str = ""
    quantity_bbl: float = 0.0
    po_number: Optional[str] = Field(default=None, index=True)
    received_at: datetime = Field(default_factory=datetime.utcnow)


class TankReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tank_id: str = Field(index=True)
    terminal: str
    reading_date: date = date.today()
    quantity_bbl: float = 0.0
    method: str = "sensor"  # "sensor" | "manual_gauge"
    po_number: Optional[str] = Field(default=None, index=True)


# --- WMS -----------------------------------------------------------------------------
class WMSInventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_code: str = Field(index=True)
    warehouse: str
    bin_location: str = ""
    quantity_on_hand: float = 0.0


# --- CRM -------------------------------------------------------------------------------
class CRMCustomer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_code: str = Field(index=True)  # mirrors a mock-sap Customer.customer_code
    name: str
    segment: str = "Standard"
    account_manager: str = ""


class CRMOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(index=True, unique=True)
    customer_code: str = Field(index=True)
    amount: float = 0.0
    status: str = "Open"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Supplier Portal --------------------------------------------------------------------
class SupplierDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_code: str = Field(index=True)
    document_type: str  # "GST Certificate" | "Insurance Certificate" | "MSDS" | "Bank Letter"
    filename: str
    status: str = "Pending"  # "Pending" | "Approved" | "Rejected"
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class SupplierOnboardingSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    vendor_name: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Submitted"


# --- Email -------------------------------------------------------------------------------
class EmailMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str
    sender_name: str = ""
    subject: str
    body: str = ""
    department: str = ""
    has_attachment: bool = Field(default=False)
    received_at: datetime = Field(default_factory=datetime.utcnow, index=True)


# --- LIMS ----------------------------------------------------------------------------------
class LIMSResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sample_id: str = Field(index=True, unique=True)
    test_type: str
    result_value: float = 0.0
    unit: str = ""
    pass_fail: str = "Pass"
    location: str = ""
    tested_at: datetime = Field(default_factory=datetime.utcnow)


# --- Document Repository ----------------------------------------------------------------------
class DocumentRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: str = Field(index=True, unique=True)
    title: str
    category: str = "General"
    file_type: str = "pdf"
    created_at: datetime = Field(default_factory=datetime.utcnow)
