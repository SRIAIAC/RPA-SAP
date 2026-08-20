import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

import app.main as main_module
from app.database import get_session
from app.main import app
from app.seed.generate_synthetic_data import seed_all

TEST_ENGINE = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
main_module.engine = TEST_ENGINE


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    SQLModel.metadata.create_all(TEST_ENGINE)
    with Session(TEST_ENGINE) as session:
        seed_all(session, scale="small")
    yield


def _get_test_session():
    with Session(TEST_ENGINE) as session:
        yield session


app.dependency_overrides[get_session] = _get_test_session


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
