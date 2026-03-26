from uuid import uuid4

from aces_backend.domain.models import (
    AircraftState,
    MatchState,
    Phase,
    PilotState,
    PlayerState,
    RunwayState,
    WeaponState,
    Zone,
)


def build_seeded_match(
    match_id: str | None = None,
    cp_per_turn: int = 2,
    runway_health: int = 20,
) -> MatchState:
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
                runway=RunwayState(health=runway_health, max_health=runway_health),
                command_points=cp_per_turn,
                aircraft=[
                    AircraftState(
                        aircraft_id="aircraft-alpha",
                        owner_player_id="player-1",
                        name="Falcon One",
                        fuel=6,
                        max_fuel=6,
                        structure_rating=4,
                        attack=3,
                        evasion=4,
                        zone=Zone.RUNWAY,
                        weapon=WeaponState(
                            weapon_id="weapon-alpha-cannon",
                            name="20mm Cannon",
                            attack_bonus=1,
                            damage=2,
                        ),
                        pilot=PilotState(
                            pilot_id="pilot-alpha",
                            name="Maverick",
                            attack_bonus=1,
                        ),
                    ),
                    AircraftState(
                        aircraft_id="aircraft-charlie",
                        owner_player_id="player-1",
                        name="Eagle Three",
                        fuel=4,
                        max_fuel=4,
                        structure_rating=3,
                        attack=2,
                        evasion=4,
                        zone=Zone.RUNWAY,
                    ),
                ],
            ),
            PlayerState(
                player_id="player-2",
                display_name="Player Two",
                runway=RunwayState(health=runway_health, max_health=runway_health),
                command_points=cp_per_turn,
                aircraft=[
                    AircraftState(
                        aircraft_id="aircraft-bravo",
                        owner_player_id="player-2",
                        name="Viper Two",
                        fuel=5,
                        max_fuel=5,
                        structure_rating=4,
                        attack=2,
                        evasion=4,
                        zone=Zone.RUNWAY,
                        weapon=WeaponState(
                            weapon_id="weapon-bravo-missile",
                            name="Sidewinder Missile",
                            attack_bonus=2,
                            damage=3,
                        ),
                    ),
                    AircraftState(
                        aircraft_id="aircraft-delta",
                        owner_player_id="player-2",
                        name="Hawk Four",
                        fuel=4,
                        max_fuel=4,
                        structure_rating=3,
                        attack=3,
                        evasion=4,
                        zone=Zone.RUNWAY,
                    ),
                ],
            ),
        ],
    )
