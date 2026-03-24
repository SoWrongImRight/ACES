from functools import lru_cache

from aces_backend.domain.repository import MatchRepository
from aces_backend.rules.engine import RulesEngine


@lru_cache
def get_match_repository() -> MatchRepository:
    return MatchRepository()


@lru_cache
def get_rules_engine() -> RulesEngine:
    return RulesEngine()
