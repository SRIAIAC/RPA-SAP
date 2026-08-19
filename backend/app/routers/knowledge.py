from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"

DEPARTMENTS = [
    "procurement",
    "production",
    "hse",
    "material_management",
    "warehouse_management",
    "sales_distribution",
    "supply_chain_management",
    "finance",
    "maintenance",
]


@router.get("")
def list_departments(user: User = Depends(get_current_user)):
    return {"departments": DEPARTMENTS}


@router.get("/{department}", response_class=PlainTextResponse)
def get_department_kb(department: str, user: User = Depends(get_current_user)):
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=404, detail="Unknown department knowledge base")
    path = KB_DIR / f"{department}.md"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Knowledge base file missing")
    return path.read_text(encoding="utf-8")
