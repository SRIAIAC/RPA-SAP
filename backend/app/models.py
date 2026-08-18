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
