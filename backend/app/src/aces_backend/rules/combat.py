from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from aces_backend.domain.models import (
    AircraftState,
    AttackTargetType,
    MatchEvent,
    MatchState,
    PlayerState,
    Zone,
)


@dataclass(slots=True)
class CombatInput:
    action_type: str
    actor_player_id: str
    attacking_aircraft_id: str
    target_type: AttackTargetType
    target_id: str
    base_attack: int
    base_evasion: int | None
    resolved_attack: int
    resolved_evasion: int | None
    weapon_damage: int = 1


@dataclass(slots=True)
class CombatStatModifier:
    category: "CombatModifierCategory"
    source: str
    attack_delta: int = 0
    evasion_delta: int = 0


class CombatModifierCategory(StrEnum):
    PILOT = "pilot"
    WEAPON = "weapon"
    AIRFRAME = "airframe"
    TEMPORARY_EFFECT = "temporary_effect"
    HAZARD_DEBUFF = "hazard_debuff"


COMBAT_MODIFIER_CATEGORY_ORDER: tuple[CombatModifierCategory, ...] = (
    CombatModifierCategory.PILOT,
    CombatModifierCategory.WEAPON,
    CombatModifierCategory.AIRFRAME,
    CombatModifierCategory.TEMPORARY_EFFECT,
    CombatModifierCategory.HAZARD_DEBUFF,
)


@dataclass(slots=True)
class CombatInputBuilder:
    """Builds canonical combat inputs before resolution and future modifiers."""

    def build_attack_input(
        self,
        *,
        action_type: str,
        actor_player_id: str,
        attacking_aircraft_id: str,
        target_type: AttackTargetType,
        target_id: str,
        attacking_aircraft: AircraftState | None,
        target_aircraft: AircraftState | None,
        extra_modifiers: list[CombatStatModifier] | None = None,
    ) -> CombatInput:
        base_attack = attacking_aircraft.attack if attacking_aircraft is not None else 0
        base_evasion = (
            target_aircraft.evasion
            if target_type == AttackTargetType.AIRCRAFT and target_aircraft is not None
            else None
        )
        resolved_attack, resolved_evasion = self._apply_ordered_modifiers(
            base_attack=base_attack,
            base_evasion=base_evasion,
            modifiers=[
                *self._gather_attack_modifiers(
                    attacking_aircraft=attacking_aircraft,
                    target_aircraft=target_aircraft,
                    target_type=target_type,
                    target_id=target_id,
                ),
                *(extra_modifiers or []),
            ],
        )
        weapon_damage = (
            attacking_aircraft.weapon.damage
            if attacking_aircraft is not None
            and attacking_aircraft.weapon is not None
            and not attacking_aircraft.weapon.exhausted
            else 1
        )
        return CombatInput(
            action_type=action_type,
            actor_player_id=actor_player_id,
            attacking_aircraft_id=attacking_aircraft_id,
            target_type=target_type,
            target_id=target_id,
            base_attack=base_attack,
            base_evasion=base_evasion,
            resolved_attack=resolved_attack,
            resolved_evasion=resolved_evasion,
            weapon_damage=weapon_damage,
        )

    def _gather_attack_modifiers(
        self,
        *,
        attacking_aircraft: AircraftState | None,
        target_aircraft: AircraftState | None,
        target_type: AttackTargetType,
        target_id: str,
    ) -> list[CombatStatModifier]:
        del target_aircraft, target_type, target_id

        return collect_attachment_attack_modifiers(attacking_aircraft=attacking_aircraft)

    def _apply_ordered_modifiers(
        self,
        *,
        base_attack: int,
        base_evasion: int | None,
        modifiers: list[CombatStatModifier],
    ) -> tuple[int, int | None]:
        resolved_attack = base_attack
        resolved_evasion = base_evasion

        for modifier in order_combat_modifiers(modifiers):
            resolved_attack += modifier.attack_delta
            if resolved_evasion is not None:
                resolved_evasion += modifier.evasion_delta

        return resolved_attack, resolved_evasion


def order_combat_modifiers(
    modifiers: list[CombatStatModifier],
) -> list[CombatStatModifier]:
    category_index = {
        category: index for index, category in enumerate(COMBAT_MODIFIER_CATEGORY_ORDER)
    }
    return sorted(
        modifiers,
        key=lambda modifier: category_index.get(
            modifier.category,
            len(COMBAT_MODIFIER_CATEGORY_ORDER),
        ),
    )


def collect_attachment_attack_modifiers(
    *,
    attacking_aircraft: AircraftState | None,
) -> list[CombatStatModifier]:
    if attacking_aircraft is None:
        return []

    return order_combat_modifiers(
        [
            *collect_pilot_attack_modifiers(attacking_aircraft=attacking_aircraft),
            *collect_weapon_attack_modifiers(attacking_aircraft=attacking_aircraft),
        ]
    )


def collect_pilot_attack_modifiers(
    *,
    attacking_aircraft: AircraftState | None,
) -> list[CombatStatModifier]:
    if (
        attacking_aircraft is None
        or attacking_aircraft.pilot is None
        or attacking_aircraft.pilot.attack_bonus == 0
    ):
        return []

    return [
        CombatStatModifier(
            category=CombatModifierCategory.PILOT,
            source=f"pilot:{attacking_aircraft.pilot.pilot_id}",
            attack_delta=attacking_aircraft.pilot.attack_bonus,
        )
    ]


def collect_weapon_attack_modifiers(
    *,
    attacking_aircraft: AircraftState | None,
) -> list[CombatStatModifier]:
    if (
        attacking_aircraft is None
        or attacking_aircraft.weapon is None
        or attacking_aircraft.weapon.exhausted
        or attacking_aircraft.weapon.attack_bonus == 0
    ):
        return []

    return [
        CombatStatModifier(
            category=CombatModifierCategory.WEAPON,
            source=f"weapon:{attacking_aircraft.weapon.weapon_id}",
            attack_delta=attacking_aircraft.weapon.attack_bonus,
        )
    ]


@dataclass(slots=True)
class CombatResult:
    action_type: str
    actor_player_id: str
    attacking_aircraft_id: str
    target_type: AttackTargetType
    target_id: str
    outcome_type: str
    structure_rating_delta: int = 0
    runway_damage: int = 0
    destroyed_entity_id: str | None = None
    winner_player_id: str | None = None

    @property
    def is_hit(self) -> bool:
        return self.outcome_type in {"hit", "runway_hit"}


def build_attack_combat_input(
    *,
    action_type: str,
    actor_player_id: str,
    attacking_aircraft_id: str,
    target_type: AttackTargetType,
    target_id: str,
    attacking_aircraft: AircraftState | None,
    target_aircraft: AircraftState | None,
) -> CombatInput:
    return CombatInputBuilder().build_attack_input(
        action_type=action_type,
        actor_player_id=actor_player_id,
        attacking_aircraft_id=attacking_aircraft_id,
        target_type=target_type,
        target_id=target_id,
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )


def resolve_attack_combat_result(
    *,
    combat_input: CombatInput,
    target_aircraft: AircraftState | None,
    target_player: PlayerState | None,
    match_state: MatchState,
) -> CombatResult:
    hit = _resolve_attack_hit(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
    )
    structure_rating_delta = (
        -combat_input.weapon_damage if hit and combat_input.target_type == AttackTargetType.AIRCRAFT else 0
    )
    runway_damage = (
        combat_input.weapon_damage if hit and combat_input.target_type == AttackTargetType.RUNWAY else 0
    )
    destroyed_entity_id = _destroyed_entity_id_for_attack(
        target_type=combat_input.target_type,
        target_id=combat_input.target_id,
        target_aircraft=target_aircraft,
        target_player=target_player,
        structure_rating_delta=structure_rating_delta,
        runway_damage=runway_damage,
    )
    winner_player_id = _winner_player_id_for_attack(
        actor_player_id=combat_input.actor_player_id,
        target_type=combat_input.target_type,
        target_id=combat_input.target_id,
        target_aircraft=target_aircraft,
        match_state=match_state,
        destroyed_entity_id=destroyed_entity_id,
    )
    return CombatResult(
        action_type=combat_input.action_type,
        actor_player_id=combat_input.actor_player_id,
        attacking_aircraft_id=combat_input.attacking_aircraft_id,
        target_type=combat_input.target_type,
        target_id=combat_input.target_id,
        outcome_type=(
            "hit"
            if hit and combat_input.target_type == AttackTargetType.AIRCRAFT
            else "runway_hit"
            if hit
            else "miss"
        ),
        structure_rating_delta=structure_rating_delta,
        runway_damage=runway_damage,
        destroyed_entity_id=destroyed_entity_id,
        winner_player_id=winner_player_id,
    )


def apply_terminal_outcome_to_combat_result(
    *,
    combat_result: CombatResult,
    match_state: MatchState,
) -> CombatResult:
    if not match_state.is_terminal:
        return combat_result

    return CombatResult(
        action_type=combat_result.action_type,
        actor_player_id=combat_result.actor_player_id,
        attacking_aircraft_id=combat_result.attacking_aircraft_id,
        target_type=combat_result.target_type,
        target_id=combat_result.target_id,
        outcome_type=combat_result.outcome_type,
        structure_rating_delta=combat_result.structure_rating_delta,
        runway_damage=combat_result.runway_damage,
        destroyed_entity_id=combat_result.destroyed_entity_id,
        winner_player_id=match_state.winner_player_id,
    )


def combat_result_to_action_resolution_fields(
    *,
    combat_result: CombatResult,
    updated_target_aircraft: AircraftState | None,
    updated_target_player: PlayerState | None,
) -> dict[str, Any]:
    return {
        "target_type": combat_result.target_type,
        "target_id": combat_result.target_id,
        "executed": True,
        "result_type": combat_result.outcome_type,
        "structure_rating_change": (
            combat_result.structure_rating_delta
            if combat_result.target_type == AttackTargetType.AIRCRAFT
            else None
        ),
        "target_structure_rating": (
            updated_target_aircraft.structure_rating
            if updated_target_aircraft is not None
            else None
        ),
        "runway_health_change": (
            -combat_result.runway_damage
            if combat_result.target_type == AttackTargetType.RUNWAY
            and combat_result.runway_damage > 0
            else None
        ),
        "target_runway_health": (
            updated_target_player.runway.health
            if updated_target_player is not None
            else None
        ),
        "target_destroyed": combat_result.destroyed_entity_id is not None,
    }


def combat_result_to_events(
    *,
    combat_result: CombatResult,
) -> list[MatchEvent]:
    events = [
        MatchEvent(
            sequence=0,
            action_type=combat_result.action_type,
            actor_player_id=combat_result.actor_player_id,
            actor_entity_id=combat_result.attacking_aircraft_id,
            target_type=combat_result.target_type,
            target_id=combat_result.target_id,
            outcome_type=combat_result.outcome_type,
            from_zone=Zone.AIR,
            to_zone=Zone.AIR,
            sr_delta=(
                combat_result.structure_rating_delta
                if combat_result.target_type == AttackTargetType.AIRCRAFT
                else None
            ),
            runway_damage=(
                combat_result.runway_damage
                if combat_result.target_type == AttackTargetType.RUNWAY
                and combat_result.runway_damage > 0
                else None
            ),
        )
    ]

    if (
        combat_result.destroyed_entity_id is not None
        and combat_result.target_type == AttackTargetType.AIRCRAFT
    ):
        events.append(
            MatchEvent(
                sequence=0,
                action_type=combat_result.action_type,
                actor_player_id=combat_result.actor_player_id,
                actor_entity_id=combat_result.attacking_aircraft_id,
                target_type=combat_result.target_type,
                target_id=combat_result.target_id,
                outcome_type="entity_destroyed",
                destroyed_entity_id=combat_result.destroyed_entity_id,
            )
        )

    if combat_result.winner_player_id is not None:
        events.append(
            MatchEvent(
                sequence=0,
                action_type=combat_result.action_type,
                actor_player_id=combat_result.actor_player_id,
                actor_entity_id=combat_result.attacking_aircraft_id,
                target_type=combat_result.target_type,
                target_id=combat_result.target_id,
                outcome_type="match_won",
                winner_player_id=combat_result.winner_player_id,
            )
        )

    return events


def _resolve_attack_hit(
    *,
    combat_input: CombatInput,
    target_aircraft: AircraftState | None,
) -> bool:
    if combat_input.resolved_attack <= 0:
        return False

    if combat_input.target_type == AttackTargetType.RUNWAY:
        return True

    return (
        target_aircraft is not None
        and not target_aircraft.destroyed
        and combat_input.resolved_evasion is not None
        and combat_input.resolved_attack >= combat_input.resolved_evasion
    )


def _destroyed_entity_id_for_attack(
    *,
    target_type: AttackTargetType,
    target_id: str,
    target_aircraft: AircraftState | None,
    target_player: PlayerState | None,
    structure_rating_delta: int,
    runway_damage: int,
) -> str | None:
    if target_type == AttackTargetType.AIRCRAFT and target_aircraft is not None:
        next_structure_rating = target_aircraft.structure_rating + structure_rating_delta
        return target_id if structure_rating_delta < 0 and next_structure_rating <= 0 else None

    if target_type == AttackTargetType.RUNWAY and target_player is not None:
        next_runway_health = target_player.runway.health - runway_damage
        return target_id if runway_damage > 0 and next_runway_health <= 0 else None

    return None


def _winner_player_id_for_attack(
    *,
    actor_player_id: str,
    target_type: AttackTargetType,
    target_id: str,
    target_aircraft: AircraftState | None,
    match_state: MatchState,
    destroyed_entity_id: str | None,
) -> str | None:
    if destroyed_entity_id is None:
        return None

    if target_type == AttackTargetType.RUNWAY:
        return actor_player_id

    if target_aircraft is None:
        return None

    defending_player = target_aircraft.owner_player_id
    defending_state = match_state.get_player(defending_player)
    if defending_state is None:
        return None

    surviving_other_aircraft = [
        aircraft
        for aircraft in defending_state.aircraft
        if aircraft.aircraft_id != target_id and not aircraft.destroyed
    ]
    if surviving_other_aircraft:
        return None

    return actor_player_id
