from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import TankReading, TerminalReceipt

router = APIRouter(prefix="/api/terminal", tags=["Terminal"])


@router.get("/receipts")
def list_receipts(
    po_number: Optional[str] = None, terminal: Optional[str] = None, session: Session = Depends(get_session)
):
    stmt = select(TerminalReceipt)
    if po_number is not None:
        stmt = stmt.where(TerminalReceipt.po_number == po_number)
    if terminal is not None:
        stmt = stmt.where(TerminalReceipt.terminal == terminal)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]


@router.get("/tank-readings")
def list_tank_readings(
    po_number: Optional[str] = None, tank_id: Optional[str] = None, session: Session = Depends(get_session)
):
    stmt = select(TankReading)
    if po_number is not None:
        stmt = stmt.where(TankReading.po_number == po_number)
    if tank_id is not None:
        stmt = stmt.where(TankReading.tank_id == tank_id)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]
