from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.numbering import generate_number
from app.models import Customer, SalesOrder, SalesOrderItem

router = APIRouter(prefix="/api/sd", tags=["SAP SD"])


@router.get("/customers/{customer_code}")
def get_customer(customer_code: str, session: Session = Depends(get_session)):
    customer = session.exec(select(Customer).where(Customer.customer_code == customer_code)).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer.model_dump(mode="json")


@router.post("/sales-orders")
def create_sales_order(payload: dict, session: Session = Depends(get_session)):
    items_payload = payload.pop("items", [])
    payload.setdefault("so_number", generate_number("SO"))
    order = SalesOrder(**payload)
    session.add(order)
    session.commit()
    session.refresh(order)
    for item in items_payload:
        session.add(SalesOrderItem(so_id=order.id, **item))
    session.commit()
    session.refresh(order)
    out = order.model_dump(mode="json")
    out["items"] = items_payload
    return out
