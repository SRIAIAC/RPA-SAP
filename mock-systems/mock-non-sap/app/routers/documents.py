from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import DocumentRecord

router = APIRouter(prefix="/api/documents", tags=["Document Repository"])


@router.get("/{document_id}")
def get_document(document_id: str, session: Session = Depends(get_session)):
    doc = session.exec(select(DocumentRecord).where(DocumentRecord.document_id == document_id)).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.model_dump(mode="json")
