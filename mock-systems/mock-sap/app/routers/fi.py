from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.numbering import generate_number
from app.models import Invoice, InvoiceItem

router = APIRouter(prefix="/api/fi", tags=["SAP FI"])


def _invoice_with_items(invoice: Invoice, session: Session) -> dict:
    items = session.exec(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)).all()
    out = invoice.model_dump(mode="json")
    out["items"] = [i.model_dump(mode="json") for i in items]
    return out


@router.get("/invoices/{invoice_number}")
def get_invoice(invoice_number: str, session: Session = Depends(get_session)):
    invoice = session.exec(select(Invoice).where(Invoice.invoice_number == invoice_number)).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_with_items(invoice, session)


@router.post("/invoices")
def create_invoice(payload: dict, session: Session = Depends(get_session)):
    items_payload = payload.pop("items", [])
    payload.setdefault("invoice_number", generate_number("INV"))
    invoice = Invoice(**payload)
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    for item in items_payload:
        session.add(InvoiceItem(invoice_id=invoice.id, **item))
    session.commit()
    session.refresh(invoice)
    return _invoice_with_items(invoice, session)
