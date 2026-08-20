from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import EmailMessage

router = APIRouter(prefix="/api/email", tags=["Email"])


@router.get("/inbox")
def list_inbox(department: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(EmailMessage)
    if department is not None:
        stmt = stmt.where(EmailMessage.department == department)
    rows = session.exec(stmt.order_by(EmailMessage.received_at.desc()).limit(200)).all()
    return [r.model_dump(mode="json") for r in rows]


@router.post("/send")
def send_email(payload: dict, session: Session = Depends(get_session)):
    message = EmailMessage(
        sender="rpa-platform@petronova.example",
        sender_name="PetroNova Ops Platform",
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
        department=payload.get("department", ""),
    )
    session.add(message)
    session.commit()
    session.refresh(message)
    return message.model_dump(mode="json")
