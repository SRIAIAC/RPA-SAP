from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from app.database import engine, init_db
from app.routers import admin, auth, exceptions, runs, workflows
from app.seed_data import seed

app = FastAPI(title="RPA/SAP Ops Console", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with Session(engine) as session:
        seed(session)


app.include_router(auth.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(exceptions.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
