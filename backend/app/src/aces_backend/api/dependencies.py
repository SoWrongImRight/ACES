from functools import lru_cache
from pathlib import Path

from aces_backend.cards.loader import CardLoader
from aces_backend.cards.source import LocalFileCardSource
from aces_backend.config import GameSettings
from aces_backend.domain.sqlite_repository import SqliteMatchRepository
from aces_backend.rules.engine import RulesEngine


@lru_cache
def get_settings() -> GameSettings:
    return GameSettings()


@lru_cache
def get_card_loader() -> CardLoader:
    settings = get_settings()
    return CardLoader(LocalFileCardSource(Path(settings.cards_path)))


@lru_cache
def get_match_repository() -> SqliteMatchRepository:
    settings = get_settings()
    return SqliteMatchRepository(db_path=settings.db_path)


@lru_cache
def get_rules_engine() -> RulesEngine:
    return RulesEngine()
