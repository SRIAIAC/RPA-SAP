from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import ProductionOrder, ProductionRecord

router = APIRouter(prefix="/api/pp", tags=["SAP PP"])


@router.get("/production-orders")
def list_production_orders(
    plant: Optional[str] = None, status: Optional[str] = None, session: Session = Depends(get_session)
):
    stmt = select(ProductionOrder)
    if plant is not None:
        stmt = stmt.where(ProductionOrder.plant == plant)
    if status is not None:
        stmt = stmt.where(ProductionOrder.status == status)
    orders = session.exec(stmt.limit(500)).all()
    out = []
    for order in orders:
        records = session.exec(
            select(ProductionRecord).where(ProductionRecord.production_order_id == order.id)
        ).all()
        row = order.model_dump(mode="json")
        row["records"] = [r.model_dump(mode="json") for r in records]
        out.append(row)
    return out
