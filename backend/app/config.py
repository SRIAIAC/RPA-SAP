import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("app.config")

BACKEND_DIR = Path(__file__).resolve().parent.parent
INSECURE_DEFAULT_SECRET = "dev-only-secret-change-me"
# The docker-compose.yml default Postgres credential pair. Matched against
# DATABASE_URL (not POSTGRES_PASSWORD directly — the backend never sees that
# var, only the assembled connection string) to catch the common mistake of
# deploying with APP_ENV=production but forgetting to also override
# POSTGRES_PASSWORD in .env.
INSECURE_DEFAULT_DB_CREDENTIALS = "rpa_sap:rpa_sap@"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    secret_key: str = Field(default=INSECURE_DEFAULT_SECRET, alias="RPA_SAP_SECRET_KEY")
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR / 'rpa_sap.db').as_posix()}", alias="DATABASE_URL"
    )
    allowed_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="ALLOWED_ORIGINS"
    )
    app_env: str = Field(default="development", alias="APP_ENV")
    access_token_expire_minutes: int = Field(default=60 * 8, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")

    # --- Platform mode + provider selection ---------------------------------
    # APP_MODE is informational/display-only (shown in System Health); it does
    # not gate behavior. Provider selection is driven by the *_PROVIDER vars
    # directly. All default to "mock" and require no external credentials.
    app_mode: str = Field(default="demo", alias="APP_MODE")
    sap_provider: str = Field(default="mock", alias="SAP_PROVIDER")
    ai_provider: str = Field(default="mock", alias="AI_PROVIDER")
    rpa_provider: str = Field(default="mock", alias="RPA_PROVIDER")
    event_bus: str = Field(default="inmemory", alias="EVENT_BUS")

    # --- Mock service locations ----------------------------------------------
    mock_sap_base_url: str = Field(default="http://127.0.0.1:8100", alias="MOCK_SAP_BASE_URL")
    mock_non_sap_base_url: str = Field(
        default="http://127.0.0.1:8200", alias="MOCK_NON_SAP_BASE_URL"
    )

    # --- Future real-provider placeholders ------------------------------------
    # Never required while the corresponding *_PROVIDER setting is "mock".
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    sap_base_url: Optional[str] = Field(default=None, alias="SAP_BASE_URL")
    sap_client_id: Optional[str] = Field(default=None, alias="SAP_CLIENT_ID")
    sap_client_secret: Optional[str] = Field(default=None, alias="SAP_CLIENT_SECRET")
    uipath_base_url: Optional[str] = Field(default=None, alias="UIPATH_BASE_URL")

    # --- Optional: real Gmail read-only import (Mailroom testing) ------------
    # Both unset by default -> the /api/mailroom/import-gmail endpoint returns
    # a 400 explaining what to set. gmail_app_password MUST be a Google
    # "App Password" (Google Account -> Security -> App passwords, requires
    # 2FA), never the actual account password.
    gmail_address: Optional[str] = Field(default=None, alias="GMAIL_ADDRESS")
    gmail_app_password: Optional[str] = Field(default=None, alias="GMAIL_APP_PASSWORD")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _fail_fast_on_insecure_production_config(self) -> "Settings":
        if self.app_env != "production":
            return self

        if self.secret_key == INSECURE_DEFAULT_SECRET:
            raise RuntimeError(
                "RPA_SAP_SECRET_KEY must be set to a non-default value when APP_ENV=production. "
                "Refusing to start with the insecure default secret key. "
                "Generate one with: python scripts/generate_secret_key.py"
            )
        if INSECURE_DEFAULT_DB_CREDENTIALS in self.database_url:
            raise RuntimeError(
                "DATABASE_URL still uses the default rpa_sap/rpa_sap credential pair while "
                "APP_ENV=production. Set POSTGRES_PASSWORD (and rebuild DATABASE_URL) to a "
                "non-default value before deploying."
            )
        if self.allowed_origins_list == ["http://localhost:5173", "http://127.0.0.1:5173"]:
            logger.warning(
                "ALLOWED_ORIGINS is still the localhost dev default in a production environment; "
                "the real frontend origin will be rejected by CORS until this is overridden."
            )
        return self


settings = Settings()
