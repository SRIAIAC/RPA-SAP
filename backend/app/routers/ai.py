"""AI Decisions — lists AIDecision rows written by AIService on every
MockAIProvider call, for the AI Decisions page / run-detail decision trace."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.deps import require_min_level
from app.models import Level, User
from app.models_platform import AIDecision

router = APIRouter(prefix="/api/ai", tags=["ai"])

_min_level_dep = require_min_level(Level.SENIOR_MANAGER)


@router.get("/decisions")
def list_ai_decisions(
    use_case: Optional[str] = None,
    workflow_run_id: Optional[int] = None,
    limit: int = 200,
    session: Session = Depends(get_session),
    user: User = Depends(_min_level_dep),
):
    stmt = select(AIDecision)
    if use_case is not None:
        stmt = stmt.where(AIDecision.use_case == use_case)
    if workflow_run_id is not None:
        stmt = stmt.where(AIDecision.workflow_run_id == workflow_run_id)
    rows = session.exec(stmt.order_by(AIDecision.created_at.desc()).limit(limit)).all()
    return [row.model_dump(mode="json") for row in rows]
