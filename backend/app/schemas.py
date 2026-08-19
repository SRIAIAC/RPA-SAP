from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models import Department, ExceptionStatus, Level, RunStatus


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: Department
    level: Level
    active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class WorkflowOut(BaseModel):
    id: int
    key: str
    name: str
    department: Department
    description: str
    sap_systems: str
    non_sap_systems: str
    steps: List[str]
    can_run: bool

    class Config:
        from_attributes = True


class RunOut(BaseModel):
    id: int
    workflow_id: int
    workflow_name: str
    triggered_by_id: int
    triggered_by_name: str
    department: Department
    status: RunStatus
    current_step: int
    total_steps: int
    log: List[dict]
    started_at: datetime
    finished_at: Optional[datetime]
    result_summary: Optional[str]

    class Config:
        from_attributes = True


class ExceptionOut(BaseModel):
    id: int
    run_id: int
    workflow_id: int
    workflow_name: str
    department: Department
    reason: str
    status: ExceptionStatus
    raised_at: datetime
    resolved_at: Optional[datetime]
    resolved_by_name: Optional[str]
    resolution_note: Optional[str]

    class Config:
        from_attributes = True


class ExceptionResolve(BaseModel):
    resolution_note: str


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    department: Department
    level: Level


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    level: Optional[Level] = None
    active: Optional[bool] = None
    password: Optional[str] = None


class WorkflowAccessUpdate(BaseModel):
    workflow_ids: List[int]


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: Optional[int]
    actor_name: str
    action: str
    target_type: str
    target_id: Optional[int]
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    department: Department
    workflows_available: int
    runs_today: int
    completed_today: int
    open_exceptions: int
