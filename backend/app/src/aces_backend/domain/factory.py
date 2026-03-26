from __future__ import annotations

from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from aces_backend.cards.definitions import (
        AircraftCardDefinition,
        PilotCardDefinition,
        WeaponCardDefinition,
    )
    from aces_backend.cards.loader import CardLoader


# Seeded lineup: maps instance IDs to card IDs and attachment card IDs.
# Instance IDs are stable match-state identifiers; card IDs reference definitions.
_SEEDED_LINEUP: list[dict] = [
    {
        "player_id": "player-1",
        "display_name": "Player One",
        "aircraft": [
            {
                "instance_id": "aircraft-alpha",
                "card_id": "falcon-one",
                "weapon": {"instance_id": "weapon-alpha-cannon", "card_id": "20mm-cannon"},
                "pilot": {"instance_id": "pilot-alpha", "card_id": "maverick"},
            },
            {
                "instance_id": "aircraft-charlie",
                "card_id": "eagle-three",
            },
        ],
    },
    {
        "player_id": "player-2",
        "display_name": "Player Two",
        "aircraft": [
            {
                "instance_id": "aircraft-bravo",
                "card_id": "viper-two",
                "weapon": {"instance_id": "weapon-bravo-missile", "card_id": "sidewinder-missile"},
            },
            {
                "instance_id": "aircraft-delta",
                "card_id": "hawk-four",
            },
        ],
    },
]


def build_seeded_match(
    match_id: str | None = None,
    cp_per_turn: int = 2,
    runway_health: int = 20,
    card_loader: CardLoader | None = None,
) -> MatchState:
    resolved_match_id = match_id or f"match-{uuid4().hex[:8]}"
    if card_loader is not None:
        return _build_from_lineup(
            match_id=resolved_match_id,
            cp_per_turn=cp_per_turn,
            runway_health=runway_health,
            card_loader=card_loader,
        )
    return _build_hardcoded(
        match_id=resolved_match_id,
        cp_per_turn=cp_per_turn,
        runway_health=runway_health,
    )


def _build_from_lineup(
    match_id: str,
    cp_per_turn: int,
    runway_health: int,
    card_loader: CardLoader,
) -> MatchState:
    players = []
    for player_entry in _SEEDED_LINEUP:
        aircraft_list = []
        for slot in player_entry["aircraft"]:
            card = card_loader.find_aircraft(slot["card_id"])
            if card is None:
                raise ValueError(f"Card not found: {slot['card_id']!r}")

            weapon_slot = slot.get("weapon")
            weapon = _build_weapon_state(card_loader, weapon_slot) if weapon_slot else None

            pilot_slot = slot.get("pilot")
            pilot = _build_pilot_state(card_loader, pilot_slot) if pilot_slot else None

            aircraft_list.append(_aircraft_from_card(
                instance_id=slot["instance_id"],
                owner_player_id=player_entry["player_id"],
                card=card,
                weapon=weapon,
                pilot=pilot,
            ))

        players.append(PlayerState(
            player_id=player_entry["player_id"],
            display_name=player_entry["display_name"],
            runway=RunwayState(health=runway_health, max_health=runway_health),
            command_points=cp_per_turn,
            aircraft=aircraft_list,
        ))

    return MatchState(
        match_id=match_id,
        turn_number=1,
        active_player_id="player-1",
        phase=Phase.COMMAND,
        players=players,
    )


def _aircraft_from_card(
    instance_id: str,
    owner_player_id: str,
    card: AircraftCardDefinition,
    weapon: WeaponState | None,
    pilot: PilotState | None,
) -> AircraftState:
    return AircraftState(
        aircraft_id=instance_id,
        owner_player_id=owner_player_id,
        name=card.name,
        fuel=card.max_fuel,
        max_fuel=card.max_fuel,
        structure_rating=card.structure_rating,
        attack=card.attack,
        evasion=card.evasion,
        zone=Zone.RUNWAY,
        weapon=weapon,
        pilot=pilot,
    )


def _build_weapon_state(
    card_loader: CardLoader,
    slot: dict,
) -> WeaponState:
    card = card_loader.find_weapon(slot["card_id"])
    if card is None:
        raise ValueError(f"Weapon card not found: {slot['card_id']!r}")
    return WeaponState(
        weapon_id=slot["instance_id"],
        name=card.name,
        attack_bonus=card.attack_bonus,
        damage=card.damage,
    )


def _build_pilot_state(
    card_loader: CardLoader,
    slot: dict,
) -> PilotState:
    card = card_loader.find_pilot(slot["card_id"])
    if card is None:
        raise ValueError(f"Pilot card not found: {slot['card_id']!r}")
    return PilotState(
        pilot_id=slot["instance_id"],
        name=card.name,
        attack_bonus=card.attack_bonus,
    )


def _build_hardcoded(
    match_id: str,
    cp_per_turn: int,
    runway_health: int,
) -> MatchState:
    return MatchState(
        match_id=match_id,
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
