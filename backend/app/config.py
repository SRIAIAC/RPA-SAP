from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
INSECURE_DEFAULT_SECRET = "dev-only-secret-change-me"


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

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _fail_fast_on_insecure_prod_secret(self) -> "Settings":
        if self.app_env == "production" and self.secret_key == INSECURE_DEFAULT_SECRET:
            raise RuntimeError(
                "RPA_SAP_SECRET_KEY must be set to a non-default value when APP_ENV=production. "
                "Refusing to start with the insecure default secret key."
            )
        return self


settings = Settings()
