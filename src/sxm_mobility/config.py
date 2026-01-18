from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Configure via environment variables or a local .env (not committed).
    """

    model_config = SettingsConfigDict(env_prefix="SXM_", extra="ignore")

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])

    # Data paths
    data_dir: Path = Field(default_factory=lambda: Path("data"))

    # Geography
    place_query: str = "Sint Maarten"
    network_type: str = "drive"  # osmnx: drive, walk, bike, all

    # Assignment
    bpr_alpha: float = 0.15
    bpr_beta: float = 4.0

    msa_iters: int = 30


settings = Settings()
