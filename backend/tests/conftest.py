import os
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "development")
# The full suite fires far more than 120 requests/minute through the shared
# `app` instance (one RateLimitMiddleware, built once, state shared across
# every test in the process). Keep it effectively disabled here; the
# middleware's actual 429 behavior is verified in isolation in
# test_rate_limit.py against its own tiny app.
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000000")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.events.handlers as event_handlers_module
import app.workflow_engine.simulated_engine as simulated_engine_module
from app.database import get_session
from app.main import app
from app.seed_data import seed
from app.seed_data_mailroom import seed_mailroom

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    SQLModel.metadata.create_all(TEST_ENGINE)
    with Session(TEST_ENGINE) as session:
        seed(session)
        seed_mailroom(session)
    yield


def _get_test_session():
    with Session(TEST_ENGINE) as session:
        yield session


app.dependency_overrides[get_session] = _get_test_session
# The workflow-run background task (SimulatedWorkflowEngine.run) opens its
# own Session(engine) directly (it can't use a FastAPI dependency), so
# point it at the test engine too. As of the Phase 7 refactor this lives in
# app.workflow_engine.simulated_engine, not app.routers.runs.
simulated_engine_module.engine = TEST_ENGINE
# The EventBus handler that persists Event rows has the exact same
# background/out-of-DI-graph seam — it opens Session(engine) itself.
event_handlers_module.engine = TEST_ENGINE


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def login(client, username: str, password: str = "Demo@123"):
    resp = client.post("/api/auth/login", data={"username": username, "password": password})
    return resp


def auth_headers(client, username: str, password: str = "Demo@123") -> dict:
    resp = login(client, username, password)
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
