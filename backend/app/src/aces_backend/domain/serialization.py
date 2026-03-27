"""Serialize and deserialize MatchState to/from a JSON-compatible dict.

Uses dataclasses.asdict() for serialization and explicit reconstruction
for deserialization, keeping all enum values as strings.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Any

from aces_backend.domain.models import (
    ActiveBuff,
    ActiveHazard,
    AircraftState,
    AttackTargetType,
    HazardTrigger,
    MatchEvent,
    MatchState,
    Phase,
    PilotState,
    PlayerState,
    RunwayState,
    WeaponState,
    Zone,
)


def match_state_to_json(state: MatchState) -> str:
    return json.dumps(dataclasses.asdict(state))


def match_state_from_json(raw: str) -> MatchState:
    return _match_from_dict(json.loads(raw))


# --- private reconstruction helpers ---


def _match_from_dict(d: dict[str, Any]) -> MatchState:
    return MatchState(
        match_id=d["match_id"],
        turn_number=d["turn_number"],
        active_player_id=d["active_player_id"],
        phase=Phase(d["phase"]),
        is_terminal=d["is_terminal"],
        winner_player_id=d.get("winner_player_id"),
        loser_player_id=d.get("loser_player_id"),
        next_event_sequence=d.get("next_event_sequence", 1),
        players=[_player_from_dict(p) for p in d["players"]],
        event_history=[_event_from_dict(e) for e in d.get("event_history", [])],
        active_buffs=[_buff_from_dict(b) for b in d.get("active_buffs", [])],
        active_hazards=[_hazard_from_dict(h) for h in d.get("active_hazards", [])],
    )


def _player_from_dict(d: dict[str, Any]) -> PlayerState:
    return PlayerState(
        player_id=d["player_id"],
        display_name=d["display_name"],
        runway=RunwayState(
            health=d["runway"]["health"],
            max_health=d["runway"]["max_health"],
        ),
        command_points=d["command_points"],
        hand_size=d.get("hand_size", 5),
        aircraft=[_aircraft_from_dict(a) for a in d["aircraft"]],
    )


def _aircraft_from_dict(d: dict[str, Any]) -> AircraftState:
    return AircraftState(
        aircraft_id=d["aircraft_id"],
        owner_player_id=d["owner_player_id"],
        name=d["name"],
        fuel=d["fuel"],
        max_fuel=d["max_fuel"],
        structure_rating=d["structure_rating"],
        attack=d["attack"],
        evasion=d["evasion"],
        zone=Zone(d["zone"]),
        exhausted=d.get("exhausted", False),
        has_attacked_this_phase=d.get("has_attacked_this_phase", False),
        refit_this_turn=d.get("refit_this_turn", False),
        destroyed=d.get("destroyed", False),
        weapon=_weapon_from_dict(d["weapon"]) if d.get("weapon") else None,
        pilot=_pilot_from_dict(d["pilot"]) if d.get("pilot") else None,
    )


def _weapon_from_dict(d: dict[str, Any]) -> WeaponState:
    return WeaponState(
        weapon_id=d["weapon_id"],
        name=d["name"],
        attack_bonus=d["attack_bonus"],
        damage=d.get("damage", 1),
        tags=d.get("tags", []),
        exhausted=d.get("exhausted", False),
    )


def _pilot_from_dict(d: dict[str, Any]) -> PilotState:
    return PilotState(
        pilot_id=d["pilot_id"],
        name=d["name"],
        attack_bonus=d.get("attack_bonus", 0),
        evasion_bonus=d.get("evasion_bonus", 0),
        fuel_bonus=d.get("fuel_bonus", 0),
        structure_bonus=d.get("structure_bonus", 0),
    )


def _event_from_dict(d: dict[str, Any]) -> MatchEvent:
    return MatchEvent(
        sequence=d["sequence"],
        action_type=d["action_type"],
        actor_player_id=d["actor_player_id"],
        outcome_type=d["outcome_type"],
        actor_entity_id=d.get("actor_entity_id"),
        target_type=AttackTargetType(d["target_type"]) if d.get("target_type") else None,
        target_id=d.get("target_id"),
        from_zone=Zone(d["from_zone"]) if d.get("from_zone") else None,
        to_zone=Zone(d["to_zone"]) if d.get("to_zone") else None,
        sr_delta=d.get("sr_delta"),
        runway_damage=d.get("runway_damage"),
        roll=d.get("roll"),
        destroyed_entity_id=d.get("destroyed_entity_id"),
        winner_player_id=d.get("winner_player_id"),
    )


def _buff_from_dict(d: dict[str, Any]) -> ActiveBuff:
    return ActiveBuff(
        tactic_id=d["tactic_id"],
        aircraft_id=d["aircraft_id"],
        player_id=d["player_id"],
        attack_delta=d.get("attack_delta", 0),
        evasion_delta=d.get("evasion_delta", 0),
        self_damage=d.get("self_damage", 0),
    )


def _hazard_from_dict(d: dict[str, Any]) -> ActiveHazard:
    return ActiveHazard(
        hazard_id=d["hazard_id"],
        owning_player_id=d["owning_player_id"],
        trigger=HazardTrigger(d["trigger"]),
        attack_delta=d.get("attack_delta", 0),
        evasion_delta=d.get("evasion_delta", 0),
        cancels_weapon_bonus=d.get("cancels_weapon_bonus", False),
    )
