from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import WMSInventory

router = APIRouter(prefix="/api/wms", tags=["WMS"])


@router.get("/inventory")
def get_inventory(
    material_code: Optional[str] = None, warehouse: Optional[str] = None, session: Session = Depends(get_session)
):
    stmt = select(WMSInventory)
    if material_code is not None:
        stmt = stmt.where(WMSInventory.material_code == material_code)
    if warehouse is not None:
        stmt = stmt.where(WMSInventory.warehouse == warehouse)
    rows = session.exec(stmt.limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]
