import os
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.routers.runs as runs_module
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
# The workflow-run background task opens its own Session(engine) directly
# (it can't use a FastAPI dependency), so point it at the test engine too.
runs_module.engine = TEST_ENGINE


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
