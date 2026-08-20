from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import CRMCustomer, CRMOrder

router = APIRouter(prefix="/api/crm", tags=["CRM"])


@router.get("/customers")
def list_customers(customer_code: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(CRMCustomer)
    if customer_code is not None:
        stmt = stmt.where(CRMCustomer.customer_code == customer_code)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]


@router.get("/orders")
def list_orders(customer_code: Optional[str] = None, session: Session = Depends(get_session)):
    stmt = select(CRMOrder)
    if customer_code is not None:
        stmt = stmt.where(CRMOrder.customer_code == customer_code)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]
