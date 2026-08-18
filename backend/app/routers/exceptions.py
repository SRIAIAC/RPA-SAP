from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.access import can_view_department_data, visible_departments
from app.database import get_session
from app.deps import get_current_user
from app.models import ExceptionItem, ExceptionStatus, User, Workflow, WorkflowRun
from app.schemas import ExceptionOut, ExceptionResolve

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


def _to_out(item: ExceptionItem, session: Session) -> ExceptionOut:
    workflow = session.get(Workflow, item.workflow_id)
    resolver = session.get(User, item.resolved_by_id) if item.resolved_by_id else None
    return ExceptionOut(
        id=item.id,
        run_id=item.run_id,
        workflow_id=item.workflow_id,
        workflow_name=workflow.name if workflow else "Unknown",
        department=item.department,
        reason=item.reason,
        status=item.status,
        raised_at=item.raised_at,
        resolved_at=item.resolved_at,
        resolved_by_name=resolver.full_name if resolver else None,
        resolution_note=item.resolution_note,
    )


@router.get("", response_model=list[ExceptionOut])
def list_exceptions(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    depts = visible_departments(user)
    items = session.exec(
        select(ExceptionItem).where(ExceptionItem.department.in_(depts)).order_by(ExceptionItem.raised_at.desc())
    ).all()

    out = []
    for item in items:
        if can_view_department_data(user, item.department):
            out.append(_to_out(item, session))
            continue
        run = session.get(WorkflowRun, item.run_id)
        if run and run.triggered_by_id == user.id:
            out.append(_to_out(item, session))
    return out


@router.post("/{exception_id}/resolve", response_model=ExceptionOut)
def resolve_exception(
    exception_id: int,
    payload: ExceptionResolve,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = session.get(ExceptionItem, exception_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    if not can_view_department_data(user, item.department):
        raise HTTPException(status_code=403, detail="Only Senior Manager level and above can resolve exceptions")
    if item.status == ExceptionStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Exception already resolved")

    item.status = ExceptionStatus.RESOLVED
    item.resolved_at = datetime.utcnow()
    item.resolved_by_id = user.id
    item.resolution_note = payload.resolution_note
    session.add(item)
    session.commit()
    session.refresh(item)
    return _to_out(item, session)
