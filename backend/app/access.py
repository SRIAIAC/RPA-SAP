from typing import List

from sqlmodel import Session, select

from app.models import Department, Level, User, Workflow, WorkflowAccess


def visible_departments(user: User) -> List[Department]:
    if user.level == Level.ADMIN:
        return [d for d in Department if d != Department.ADMIN]
    return [user.department]


def granted_workflow_ids(session: Session, user_id: int) -> set:
    rows = session.exec(select(WorkflowAccess.workflow_id).where(WorkflowAccess.user_id == user_id))
    return set(rows.all())


def can_run_workflow(session: Session, user: User, workflow: Workflow) -> bool:
    if user.level in (Level.ADMIN,):
        return True
    if workflow.department != user.department:
        return False
    if user.level in (Level.SENIOR_MANAGER, Level.DEPT_HEAD):
        return True
    # Manager: needs explicit grant
    grant = session.exec(
        select(WorkflowAccess).where(
            WorkflowAccess.user_id == user.id,
            WorkflowAccess.workflow_id == workflow.id,
        )
    ).first()
    return grant is not None


def can_view_department_data(user: User, department: Department) -> bool:
    """Whether the user can see aggregate/department-wide runs & exceptions
    (as opposed to only their own runs)."""
    if user.level == Level.ADMIN:
        return True
    return user.department == department and user.level in (Level.SENIOR_MANAGER, Level.DEPT_HEAD)


def can_manage_department_access(user: User, department: Department) -> bool:
    """Whether the user can grant/revoke workflow access and manage users
    for the given department."""
    if user.level == Level.ADMIN:
        return True
    return user.level == Level.DEPT_HEAD and user.department == department


def can_manage_target_level(actor: User, target_level: Level) -> bool:
    if actor.level == Level.ADMIN:
        return True
    if actor.level == Level.DEPT_HEAD:
        return target_level in (Level.MANAGER, Level.SENIOR_MANAGER)
    return False
