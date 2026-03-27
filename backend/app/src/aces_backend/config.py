from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py is at backend/app/src/aces_backend/config.py — four parents up is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]


class GameSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACES_", env_file=".env", extra="ignore")

    cp_per_turn: int = 2
    runway_health: int = 20
    cards_path: str = str(_REPO_ROOT / "cards")
    db_path: str = str(_REPO_ROOT / "aces.db")
