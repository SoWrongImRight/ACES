from uuid import uuid4

from aces_backend.domain.models import (
    AircraftState,
    MatchState,
    Phase,
    PlayerState,
    RunwayState,
    Zone,
)


def build_seeded_match(match_id: str | None = None) -> MatchState:
    resolved_match_id = match_id or f"match-{uuid4().hex[:8]}"
    return MatchState(
        match_id=resolved_match_id,
        turn_number=1,
        active_player_id="player-1",
        phase=Phase.COMMAND,
        players=[
            PlayerState(
                player_id="player-1",
                display_name="Player One",
                runway=RunwayState(),
                command_points=2,
                aircraft=[
                    AircraftState(
                        aircraft_id="aircraft-alpha",
                        owner_player_id="player-1",
                        name="Falcon One",
                        fuel=6,
                        max_fuel=6,
                        structure_rating=4,
                        attack=3,
                        evasion=2,
                        zone=Zone.RUNWAY,
                    )
                ],
            ),
            PlayerState(
                player_id="player-2",
                display_name="Player Two",
                runway=RunwayState(),
                command_points=2,
                aircraft=[
                    AircraftState(
                        aircraft_id="aircraft-bravo",
                        owner_player_id="player-2",
                        name="Viper Two",
                        fuel=5,
                        max_fuel=5,
                        structure_rating=4,
                        attack=2,
                        evasion=3,
                        zone=Zone.RUNWAY,
                    )
                ],
            ),
        ],
    )
