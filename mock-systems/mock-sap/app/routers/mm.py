from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_session
from app.numbering import generate_number
from app.models import (
    Contract,
    GoodsReceipt,
    GoodsReceiptItem,
    Inventory,
    Material,
    PurchaseOrder,
    PurchaseOrderItem,
    Vendor,
)

router = APIRouter(prefix="/api/mm", tags=["SAP MM"])


@router.get("/vendors")
def list_vendors(
    blocked: Optional[bool] = None,
    department: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(Vendor)
    if blocked is not None:
        stmt = stmt.where(Vendor.blocked == blocked)
    if department is not None:
        stmt = stmt.where(Vendor.department == department)
    vendors = session.exec(stmt.limit(500)).all()
    return [v.model_dump(mode="json") for v in vendors]


@router.get("/vendors/{vendor_code}")
def get_vendor(vendor_code: str, session: Session = Depends(get_session)):
    vendor = session.exec(select(Vendor).where(Vendor.vendor_code == vendor_code)).first()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor.model_dump(mode="json")


@router.post("/vendors")
def create_vendor(payload: dict, session: Session = Depends(get_session)):
    payload.setdefault("vendor_code", generate_number("V"))
    vendor = Vendor(**payload)
    session.add(vendor)
    session.commit()
    session.refresh(vendor)
    return vendor.model_dump(mode="json")


@router.get("/materials")
def list_materials(session: Session = Depends(get_session)):
    materials = session.exec(select(Material).limit(500)).all()
    return [m.model_dump(mode="json") for m in materials]


@router.get("/materials/{material_code}")
def get_material(material_code: str, session: Session = Depends(get_session)):
    material = session.exec(select(Material).where(Material.material_code == material_code)).first()
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    return material.model_dump(mode="json")


def _po_with_items(po: PurchaseOrder, session: Session) -> dict:
    items = session.exec(
        select(PurchaseOrderItem).where(PurchaseOrderItem.po_id == po.id)
    ).all()
    out = po.model_dump(mode="json")
    out["items"] = [i.model_dump(mode="json") for i in items]
    return out


@router.get("/purchase-orders")
def list_purchase_orders(
    vendor_code: Optional[str] = None, status: Optional[str] = None, session: Session = Depends(get_session)
):
    stmt = select(PurchaseOrder)
    if vendor_code is not None:
        vendor = session.exec(select(Vendor).where(Vendor.vendor_code == vendor_code)).first()
        if vendor is None:
            return []
        stmt = stmt.where(PurchaseOrder.vendor_id == vendor.id)
    if status is not None:
        stmt = stmt.where(PurchaseOrder.status == status)
    orders = session.exec(stmt.limit(500)).all()
    return [_po_with_items(po, session) for po in orders]


@router.get("/purchase-orders/{po_number}")
def get_purchase_order(po_number: str, session: Session = Depends(get_session)):
    po = session.exec(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)).first()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return _po_with_items(po, session)


@router.post("/purchase-orders")
def create_purchase_order(payload: dict, session: Session = Depends(get_session)):
    items_payload = payload.pop("items", [])
    payload.setdefault("po_number", generate_number("PO"))
    po = PurchaseOrder(**payload)
    session.add(po)
    session.commit()
    session.refresh(po)
    for idx, item in enumerate(items_payload, start=1):
        item.setdefault("line_no", idx)
        session.add(PurchaseOrderItem(po_id=po.id, **item))
    session.commit()
    session.refresh(po)
    return _po_with_items(po, session)


@router.get("/goods-receipts/{po_number}")
def get_goods_receipt(po_number: str, session: Session = Depends(get_session)):
    po = session.exec(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)).first()
    if po is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    grn = session.exec(select(GoodsReceipt).where(GoodsReceipt.po_id == po.id)).first()
    if grn is None:
        raise HTTPException(status_code=404, detail="No goods receipt posted for this PO")
    items = session.exec(select(GoodsReceiptItem).where(GoodsReceiptItem.grn_id == grn.id)).all()
    out = grn.model_dump(mode="json")
    out["items"] = [i.model_dump(mode="json") for i in items]
    out["po_number"] = po_number
    return out


@router.get("/inventory/{material_code}")
def get_inventory(material_code: str, plant: Optional[str] = None, session: Session = Depends(get_session)):
    material = session.exec(select(Material).where(Material.material_code == material_code)).first()
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    stmt = select(Inventory).where(Inventory.material_id == material.id)
    if plant is not None:
        stmt = stmt.where(Inventory.plant == plant)
    rows = session.exec(stmt).all()
    return {
        "material_code": material_code,
        "locations": [r.model_dump(mode="json") for r in rows],
        "total_on_hand": sum(r.quantity_on_hand for r in rows),
    }


@router.get("/contracts")
def list_contracts(
    expiring_within_days: Optional[int] = Query(default=None),
    session: Session = Depends(get_session),
):
    stmt = select(Contract)
    if expiring_within_days is not None:
        cutoff = date.today() + timedelta(days=expiring_within_days)
        stmt = stmt.where(Contract.expiry_date <= cutoff).where(Contract.status == "Active")
    contracts = session.exec(stmt.limit(1000)).all()
    return [c.model_dump(mode="json") for c in contracts]


@router.get("/contracts/{contract_number}")
def get_contract(contract_number: str, session: Session = Depends(get_session)):
    contract = session.exec(select(Contract).where(Contract.contract_number == contract_number)).first()
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract.model_dump(mode="json")
