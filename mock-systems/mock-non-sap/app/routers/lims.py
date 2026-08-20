from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import LIMSResult

router = APIRouter(prefix="/api/lims", tags=["LIMS"])


@router.get("/test-results")
def list_test_results(sample_id: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(LIMSResult)
    if sample_id is not None:
        stmt = stmt.where(LIMSResult.sample_id == sample_id)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]
