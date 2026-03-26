from pydantic_settings import BaseSettings, SettingsConfigDict


class GameSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACES_", env_file=".env", extra="ignore")

    cp_per_turn: int = 2
    runway_health: int = 20
