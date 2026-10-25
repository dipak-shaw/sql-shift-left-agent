
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    azure_foundry_endpoint: Optional[str] = Field(default=None, alias="AZURE_FOUNDRY_ENDPOINT")
    azure_foundry_api_key: Optional[str] = Field(default=None, alias="AZURE_FOUNDRY_API_KEY")
    azure_foundry_model: str = Field(default="gpt-4o-mini", alias="AZURE_FOUNDRY_MODEL")
    default_runs_per_month: int = Field(default=30, alias="DEFAULT_RUNS_PER_MONTH")
    cost_per_tb_scanned_usd: float = Field(default=3.5, alias="DBU_COST_PER_TB_SCANNED_USD")
    usd_to_inr_rate: float = Field(default=85.0, alias="USD_TO_INR_RATE")
    github_token: Optional[str] = Field(default=None, alias="GITHUB_TOKEN")


settings = Settings()
