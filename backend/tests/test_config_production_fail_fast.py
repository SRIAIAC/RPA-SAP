"""Settings() must refuse to start with insecure defaults when APP_ENV=production.

Tested by constructing Settings() directly against monkeypatched env vars,
independent of the shared `app` fixture / TEST_ENGINE used by the rest of
the suite (this is pure config validation, no DB or app needed).
"""

import pytest

from app.config import Settings


def _clear_relevant_env(monkeypatch):
    for var in ("APP_ENV", "RPA_SAP_SECRET_KEY", "DATABASE_URL", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(var, raising=False)


def test_production_with_default_secret_key_refuses_to_start(monkeypatch):
    _clear_relevant_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real_user:real_pw@db:5432/rpa_sap")
    with pytest.raises(RuntimeError, match="RPA_SAP_SECRET_KEY"):
        Settings()


def test_production_with_default_db_credentials_refuses_to_start(monkeypatch):
    _clear_relevant_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RPA_SAP_SECRET_KEY", "a-real-random-production-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://rpa_sap:rpa_sap@postgres:5432/rpa_sap")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        Settings()


def test_production_with_overridden_secret_and_db_starts_cleanly(monkeypatch):
    _clear_relevant_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("RPA_SAP_SECRET_KEY", "a-real-random-production-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://real_user:real_pw@db:5432/rpa_sap")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://ops.example.com")
    settings = Settings()
    assert settings.app_env == "production"


def test_development_env_is_unaffected_by_defaults(monkeypatch):
    _clear_relevant_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    settings = Settings()
    assert settings.app_env == "development"
