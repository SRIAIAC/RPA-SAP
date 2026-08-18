from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.access import can_manage_department_access, can_manage_target_level, visible_departments
from app.auth import hash_password
from app.database import get_session
from app.deps import get_current_user, require_min_level
from app.models import Level, User, Workflow, WorkflowAccess
from app.schemas import UserCreate, UserOut, UserUpdate, WorkflowAccessUpdate, WorkflowOut
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Anyone Senior Manager or above can reach these endpoints; individual
# actions are further scoped by department/level inside each handler.
_min_level_dep = require_min_level(Level.SENIOR_MANAGER)


@router.get("/users", response_model=list[UserOut])
def list_users(session: Session = Depends(get_session), user: User = Depends(_min_level_dep)):
    depts = visible_departments(user)
    manageable_depts = [d for d in depts if can_manage_department_access(user, d)]
    if not manageable_depts:
        raise HTTPException(status_code=403, detail="No departments manageable by this account")
    users = session.exec(select(User).where(User.department.in_(manageable_depts))).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate, session: Session = Depends(get_session), user: User = Depends(_min_level_dep)
):
    if not can_manage_department_access(user, payload.department):
        raise HTTPException(status_code=403, detail="Not authorized to manage this department")
    if not can_manage_target_level(user, payload.level):
        raise HTTPException(status_code=403, detail="Not authorized to create a user at this level")
    existing = session.exec(select(User).where(User.username == payload.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        department=payload.department,
        level=payload.level,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return UserOut.model_validate(new_user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(_min_level_dep),
):
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_manage_department_access(user, target.department):
        raise HTTPException(status_code=403, detail="Not authorized to manage this department")
    if not can_manage_target_level(user, target.level):
        raise HTTPException(status_code=403, detail="Not authorized to manage this user's level")
    if payload.level is not None and not can_manage_target_level(user, payload.level):
        raise HTTPException(status_code=403, detail="Not authorized to assign this level")

    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.level is not None:
        target.level = payload.level
    if payload.active is not None:
        target.active = payload.active
    if payload.password:
        target.hashed_password = hash_password(payload.password)

    session.add(target)
    session.commit()
    session.refresh(target)
    return UserOut.model_validate(target)


@router.get("/workflows", response_model=list[WorkflowOut])
def list_all_workflows(session: Session = Depends(get_session), user: User = Depends(_min_level_dep)):
    depts = visible_departments(user)
    manageable_depts = [d for d in depts if can_manage_department_access(user, d)]
    workflows = session.exec(select(Workflow).where(Workflow.department.in_(manageable_depts))).all()
    return [
        WorkflowOut(
            id=wf.id,
            key=wf.key,
            name=wf.name,
            department=wf.department,
            description=wf.description,
            sap_systems=wf.sap_systems,
            non_sap_systems=wf.non_sap_systems,
            steps=json.loads(wf.steps_json),
            can_run=True,
        )
        for wf in workflows
    ]


@router.get("/users/{user_id}/access", response_model=list[int])
def get_user_access(
    user_id: int, session: Session = Depends(get_session), user: User = Depends(_min_level_dep)
):
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_manage_department_access(user, target.department):
        raise HTTPException(status_code=403, detail="Not authorized to manage this department")
    grants = session.exec(select(WorkflowAccess.workflow_id).where(WorkflowAccess.user_id == user_id))
    return list(grants.all())


@router.put("/users/{user_id}/access", response_model=list[int])
def set_user_access(
    user_id: int,
    payload: WorkflowAccessUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(_min_level_dep),
):
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not can_manage_department_access(user, target.department):
        raise HTTPException(status_code=403, detail="Not authorized to manage this department")
    if target.level != Level.MANAGER:
        raise HTTPException(
            status_code=400, detail="Explicit access grants only apply to Manager-level users"
        )

    # Validate every requested workflow belongs to the target's department.
    dept_workflow_ids = set(
        session.exec(select(Workflow.id).where(Workflow.department == target.department)).all()
    )
    invalid = set(payload.workflow_ids) - dept_workflow_ids
    if invalid:
        raise HTTPException(status_code=400, detail=f"Workflow ids not in department: {sorted(invalid)}")

    existing = session.exec(select(WorkflowAccess).where(WorkflowAccess.user_id == user_id)).all()
    for grant in existing:
        session.delete(grant)
    session.commit()

    for wf_id in payload.workflow_ids:
        session.add(WorkflowAccess(user_id=user_id, workflow_id=wf_id, granted_by_id=user.id))
    session.commit()

    grants = session.exec(select(WorkflowAccess.workflow_id).where(WorkflowAccess.user_id == user_id))
    return list(grants.all())
