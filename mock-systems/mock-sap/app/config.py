from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(SERVICE_DIR / ".env"), extra="ignore")

    database_url: str = Field(
        default=f"sqlite:///{(SERVICE_DIR / 'mock_sap.db').as_posix()}", alias="DATABASE_URL"
    )
    allowed_origins: str = Field(default="*", alias="ALLOWED_ORIGINS")
    seed_scale: str = Field(
        default="full", alias="SEED_SCALE"
    )  # "full" = section-4 spec volumes, "small" = fast local iteration


settings = Settings()
