from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class Department(str, Enum):
    PROCUREMENT = "Procurement"
    MAINTENANCE = "Maintenance"
    FINANCE = "Finance"
    HSE = "HSE"
    PRODUCTION = "Production"
    MATERIAL_MANAGEMENT = "Material Management"
    WAREHOUSE_MANAGEMENT = "Warehouse Management"
    SALES_DISTRIBUTION = "Sales & Distribution"
    SUPPLY_CHAIN_MANAGEMENT = "Supply Chain Management"
    ADMIN = "Admin"  # cross-department, used only by Admin-level users


class Level(str, Enum):
    MANAGER = "Manager"
    SENIOR_MANAGER = "Senior Manager"
    DEPT_HEAD = "Department Head"
    ADMIN = "Admin"


LEVEL_RANK = {
    Level.MANAGER: 0,
    Level.SENIOR_MANAGER: 1,
    Level.DEPT_HEAD: 2,
    Level.ADMIN: 3,
}


class RunStatus(str, Enum):
    RUNNING = "Running"
    COMPLETED = "Completed"
    EXCEPTION = "Exception"


class ExceptionStatus(str, Enum):
    OPEN = "Open"
    RESOLVED = "Resolved"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    department: Department
    level: Level
    active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = None


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action: str = Field(index=True)
    target_type: str
    target_id: Optional[int] = None
    detail: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Workflow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    name: str
    department: Department
    description: str
    sap_systems: str  # comma-separated, e.g. "SAP MM, SAP FI"
    non_sap_systems: str  # comma-separated, e.g. "Email, Vendor Portal"
    steps_json: str  # JSON-encoded list[str] of process steps
    exception_reasons_json: str  # JSON-encoded list[str]
    active: bool = Field(default=True)


class WorkflowAccess(SQLModel, table=True):
    """Explicit workflow grants for Manager-level users.
    Senior Manager / Department Head / Admin get implicit access to their
    whole department and do not need rows here."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    granted_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    granted_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    triggered_by_id: int = Field(foreign_key="user.id", index=True)
    department: Department
    status: RunStatus = Field(default=RunStatus.RUNNING)
    current_step: int = Field(default=0)
    log_json: str = Field(default="[]")  # JSON-encoded list of {step, ts, detail}
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    result_summary: Optional[str] = None


class ExceptionItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="workflowrun.id", index=True)
    workflow_id: int = Field(foreign_key="workflow.id", index=True)
    department: Department
    reason: str
    status: ExceptionStatus = Field(default=ExceptionStatus.OPEN)
    raised_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    resolution_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Mailroom (Part B): mock inbox + invoice OCR/triage
# ---------------------------------------------------------------------------


class MailMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str
    sender_name: str
    subject: str
    body: str
    department: Department
    received_at: datetime = Field(default_factory=datetime.utcnow)
    has_attachment: bool = Field(default=False)


class MailAttachment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mail_message_id: int = Field(foreign_key="mailmessage.id", index=True)
    filename: str
    content_type: str
    file_path: str


class InvoiceExtraction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mail_attachment_id: int = Field(foreign_key="mailattachment.id", index=True, unique=True)
    is_invoice: bool = Field(default=False)
    classifier_confidence: float = Field(default=0.0)
    classifier_reasons: str = Field(default="")
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    po_number: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
