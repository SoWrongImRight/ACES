from __future__ import annotations

from typing import TYPE_CHECKING

from aces_backend.domain.factory import build_seeded_match
from aces_backend.domain.models import MatchState

if TYPE_CHECKING:
    from aces_backend.cards.loader import CardLoader


class MatchRepository:
    """In-memory repository for local development and deterministic tests."""

    def __init__(self) -> None:
        self._matches: dict[str, MatchState] = {}

    def list_matches(self) -> list[MatchState]:
        return list(self._matches.values())

    def create_match(
        self,
        cp_per_turn: int = 2,
        runway_health: int = 20,
        card_loader: CardLoader | None = None,
    ) -> MatchState:
        match_state = build_seeded_match(
            cp_per_turn=cp_per_turn,
            runway_health=runway_health,
            card_loader=card_loader,
        )
        self._matches[match_state.match_id] = match_state
        return match_state

    def save_match(self, match_state: MatchState) -> MatchState:
        self._matches[match_state.match_id] = match_state
        return match_state

    def get_match(self, match_id: str) -> MatchState | None:
        return self._matches.get(match_id)

    def clear(self) -> None:
        self._matches.clear()
