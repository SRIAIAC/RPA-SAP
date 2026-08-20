from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app.config import settings
from app.database import engine, init_db
from app.routers import ehs, fi, mm, pm, pp, sd

app = FastAPI(title="Mock SAP", version="0.1.0")

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

    from app.models import Vendor
    from app.seed.generate_synthetic_data import seed_all

    with Session(engine) as session:
        # Idempotent: only seed a fresh database.
        if session.exec(select(Vendor)).first() is None:
            seed_all(session, scale=settings.seed_scale)


app.include_router(mm.router)
app.include_router(fi.router)
app.include_router(pm.router)
app.include_router(sd.router)
app.include_router(pp.router)
app.include_router(ehs.router)


@app.get("/api/health")
def health():
    db_status = "ok"
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"
    return {"status": "ok" if db_status == "ok" else "degraded", "db": db_status}
