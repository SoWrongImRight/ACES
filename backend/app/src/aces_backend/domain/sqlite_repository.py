"""SQLite-backed match repository.

Stores each match as a JSON blob. Uses a single persistent connection
(check_same_thread=False) so the singleton works safely under FastAPI's
default single-process, single-thread dev server.
"""
from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from aces_backend.domain.factory import build_seeded_match
from aces_backend.domain.models import MatchState
from aces_backend.domain.serialization import match_state_from_json, match_state_to_json

if TYPE_CHECKING:
    from aces_backend.cards.loader import CardLoader


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
)
"""


class SqliteMatchRepository:
    """Persistent match repository backed by a SQLite database."""

    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def list_matches(self) -> list[MatchState]:
        cursor = self._conn.execute("SELECT state_json FROM matches")
        return [match_state_from_json(row[0]) for row in cursor.fetchall()]

    def create_match(
        self,
        cp_per_turn: int = 2,
        runway_health: int = 20,
        card_loader: CardLoader | None = None,
    ) -> MatchState:
        state = build_seeded_match(
            cp_per_turn=cp_per_turn,
            runway_health=runway_health,
            card_loader=card_loader,
        )
        return self.save_match(state)

    def save_match(self, state: MatchState) -> MatchState:
        self._conn.execute(
            "INSERT OR REPLACE INTO matches (match_id, state_json) VALUES (?, ?)",
            (state.match_id, match_state_to_json(state)),
        )
        self._conn.commit()
        return state

    def get_match(self, match_id: str) -> MatchState | None:
        cursor = self._conn.execute(
            "SELECT state_json FROM matches WHERE match_id = ?",
            (match_id,),
        )
        row = cursor.fetchone()
        return match_state_from_json(row[0]) if row else None

    def clear(self) -> None:
        self._conn.execute("DELETE FROM matches")
        self._conn.commit()
