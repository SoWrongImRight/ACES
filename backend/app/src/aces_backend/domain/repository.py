from aces_backend.domain.factory import build_seeded_match
from aces_backend.domain.models import MatchState


class MatchRepository:
    """In-memory repository for local development and deterministic tests."""

    def __init__(self) -> None:
        self._matches: dict[str, MatchState] = {}

    def list_matches(self) -> list[MatchState]:
        return list(self._matches.values())

    def create_match(self) -> MatchState:
        match_state = build_seeded_match()
        self._matches[match_state.match_id] = match_state
        return match_state

    def save_match(self, match_state: MatchState) -> MatchState:
        self._matches[match_state.match_id] = match_state
        return match_state

    def get_match(self, match_id: str) -> MatchState | None:
        return self._matches.get(match_id)

    def clear(self) -> None:
        self._matches.clear()
