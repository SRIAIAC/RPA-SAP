from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import SupplierDocument, SupplierOnboardingSubmission

router = APIRouter(prefix="/api/supplier", tags=["Supplier Portal"])


@router.get("/documents")
def list_documents(vendor_id: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(SupplierDocument)
    if vendor_id is not None:
        stmt = stmt.where(SupplierDocument.vendor_code == vendor_id)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]


@router.post("/onboarding")
def submit_onboarding(payload: dict, session: Session = Depends(get_session)):
    submission = SupplierOnboardingSubmission(vendor_name=payload.get("vendor_name", "Unknown Vendor"))
    session.add(submission)
    session.commit()
    session.refresh(submission)
    return submission.model_dump(mode="json")
