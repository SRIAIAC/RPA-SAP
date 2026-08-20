import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, text

from app import models_platform  # noqa: F401  (registers new tables on SQLModel.metadata)
from app.config import settings
from app.database import engine, init_db
from app.events.handlers import persist_event_handler
from app.events.inmemory_bus import event_bus
from app.logging_config import configure_logging
from app.middleware import RateLimitMiddleware, RequestIDMiddleware, SecurityHeadersMiddleware
from app.routers import admin, ai, analytics, auth, demo, exceptions, integrations, knowledge, mailroom, runs, system, workflows
from app.seed_data import seed
from app.seed_data_mailroom import seed_mailroom

configure_logging()
logger = logging.getLogger("app.main")

app = FastAPI(title="RPA/SAP Ops Console", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.on_event("startup")
def on_startup() -> None:
    logger.info(f"Starting up (app_env={settings.app_env})")
    # Dev-friendly fallback: for real production deployments, run
    # `alembic upgrade head` instead and skip relying on create_all.
    init_db()
    with Session(engine) as session:
        seed(session)
        seed_mailroom(session)
    # EventBus wiring: SCADA alarm -> EquipmentAlarmEvent -> EventBus ->
    # this handler persists an audit-visible Event row. Registered once at
    # startup; the maintenance workflow recipe is the current publisher.
    event_bus.subscribe("equipment_alarm", persist_event_handler)


app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(exceptions.router)
app.include_router(admin.router)
app.include_router(mailroom.router)
app.include_router(knowledge.router)
app.include_router(integrations.router)
app.include_router(analytics.router)
app.include_router(demo.router)
app.include_router(ai.router)
app.include_router(system.router)


@app.get("/api/health")
def health():
    db_status = "ok"
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    overall = "ok" if db_status == "ok" else "degraded"
    return {"status": overall, "db": db_status}
