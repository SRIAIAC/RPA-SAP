from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.config import settings
from app.database import engine, init_db
from app.routers import crm, documents, email, lims, scada, supplier, terminal, wms

app = FastAPI(title="Mock Non-SAP Systems", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origins] if settings.allowed_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    from sqlmodel import select

    from app.models import SCADATelemetry
    from app.seed.generate_synthetic_data import seed_all

    with Session(engine) as session:
        if session.exec(select(SCADATelemetry)).first() is None:
            seed_all(session, scale=settings.seed_scale)


app.include_router(scada.router)
app.include_router(terminal.router)
app.include_router(wms.router)
app.include_router(crm.router)
app.include_router(supplier.router)
app.include_router(email.router)
app.include_router(lims.router)
app.include_router(documents.router)


@app.get("/api/health")
def health():
    db_status = "ok"
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}
