from collections.abc import Callable
from dataclasses import dataclass, field

from aces_backend.domain.models import ActiveBuff, AttackTargetType, MatchEvent, MatchState, Phase, PlayerState, Zone
from aces_backend.domain.services import (
    MatchHistoryManager,
    MatchOutcomeEvaluator,
    MatchStateUpdater,
)
from aces_backend.rules.combat import (
    build_attack_combat_input,
    collect_tactic_modifiers,
    CombatResult,
    CombatStatModifier,
    apply_terminal_outcome_to_combat_result,
    combat_result_to_action_resolution_fields,
    combat_result_to_events,
    resolve_attack_combat_result,
)


@dataclass(slots=True)
class TargetReference:
    target_type: AttackTargetType
    target_id: str


@dataclass(slots=True)
class ActionIntent:
    action_type: str
    actor_id: str
    player_id: str
    selected_target_ids: list[str] = field(default_factory=list)
    selected_targets: list[TargetReference] = field(default_factory=list)
    operation_name: str = ""


OPERATION_CP_COSTS: dict[str, int] = {
    "resupply": 1,
    "target-lock": 1,
    "afterburner": 1,
    "full-send": 1,
}
RESUPPLY_FUEL_AMOUNT = 3

# Tactic operations that apply a combat buff to a target aircraft.
# attack_delta: added to resolved_attack when the aircraft is attacking.
# evasion_delta: added to resolved_evasion when the aircraft is defending.
# self_damage: damage dealt to the attacking aircraft after combat resolves (if hit).
TACTIC_BUFF_DEFINITIONS: dict[str, dict] = {
    "target-lock": {"attack_delta": 2, "evasion_delta": 0, "self_damage": 0},
    "afterburner": {"attack_delta": 0, "evasion_delta": 2, "self_damage": 0},
    "full-send": {"attack_delta": 3, "evasion_delta": 0, "self_damage": 1},
}


@dataclass(slots=True)
class ActionValidationResult:
    is_valid: bool
    reason: str | None
    legal_actor_ids: list[str]
    legal_target_ids: list[str]
    legal_targets: list[TargetReference] = field(default_factory=list)


@dataclass(slots=True)
class ActionResolution:
    aircraft_id: str
    action_type: str
    previous_zone: str
    current_zone: str
    target_type: AttackTargetType | None = None
    target_id: str | None = None
    executed: bool | None = None
    result_type: str | None = None
    structure_rating_change: int | None = None
    target_structure_rating: int | None = None
    runway_health_change: int | None = None
    target_runway_health: int | None = None
    target_destroyed: bool | None = None
    fuel: int | None = None
    max_fuel: int | None = None
    exhausted: bool | None = None
    refit_this_turn: bool | None = None


@dataclass(slots=True)
class ActionExecutionResult:
    is_valid: bool
    reason: str | None
    match_state: MatchState
    resolution: ActionResolution | None
    events: list[MatchEvent] = field(default_factory=list)
    combat_result: CombatResult | None = None


class RulesEngine:
    """Centralizes backend-owned action legality and resolution."""

    def __init__(self, die_roller: Callable[[], int] | None = None) -> None:
        self._state_updater = MatchStateUpdater()
        self._outcome_evaluator = MatchOutcomeEvaluator()
        self._history_manager = MatchHistoryManager()
        self._die_roller = die_roller

    def preview_action(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionValidationResult:
        if match_state.is_terminal:
            return ActionValidationResult(
                is_valid=False,
                reason="Match is already over.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if action_intent.action_type == "attack_aircraft":
            return self._validate_attack_aircraft(
                match_state=match_state,
                player_id=action_intent.player_id,
                aircraft_id=action_intent.actor_id,
                selected_targets=self._normalized_attack_targets(action_intent),
            )

        if action_intent.action_type == "return_to_runway":
            return self._validate_return_to_runway(
                match_state=match_state,
                player_id=action_intent.player_id,
                aircraft_id=action_intent.actor_id,
                selected_target_ids=action_intent.selected_target_ids,
            )

        if action_intent.action_type == "refit_aircraft":
            return self._validate_refit_aircraft(
                match_state=match_state,
                player_id=action_intent.player_id,
                aircraft_id=action_intent.actor_id,
                selected_target_ids=action_intent.selected_target_ids,
            )

        if action_intent.action_type == "launch_aircraft":
            return self._validate_launch_aircraft(
                match_state=match_state,
                player_id=action_intent.player_id,
                aircraft_id=action_intent.actor_id,
                selected_target_ids=action_intent.selected_target_ids,
            )

        if action_intent.action_type == "play_operation":
            return self._validate_play_operation(
                match_state=match_state,
                player_id=action_intent.player_id,
                operation_name=action_intent.operation_name,
                aircraft_id=action_intent.actor_id,
            )

        if action_intent.player_id != match_state.active_player_id:

            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may submit standard actions during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        return ActionValidationResult(
            is_valid=len(action_intent.selected_target_ids) == 0,
            reason=(
                None
                if len(action_intent.selected_target_ids) == 0
                else "Full gameplay rules are not implemented yet; selected targets are not accepted."
            ),
            legal_actor_ids=[action_intent.actor_id],
            legal_target_ids=self._legal_targets_for(action_intent),
        )

    def execute_action(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        if match_state.is_terminal:
            return ActionExecutionResult(
                is_valid=False,
                reason="Match is already over.",
                match_state=match_state,
                resolution=None,
                events=[],
                combat_result=None,
            )

        if action_intent.action_type == "attack_aircraft":
            return self._execute_attack_aircraft(match_state, action_intent)

        if action_intent.action_type == "return_to_runway":
            return self._execute_return_to_runway(match_state, action_intent)

        if action_intent.action_type == "launch_aircraft":
            return self._execute_launch_aircraft(match_state, action_intent)

        if action_intent.action_type == "refit_aircraft":
            return self._execute_refit_aircraft(match_state, action_intent)

        if action_intent.action_type == "play_operation":
            return self._execute_play_operation(match_state, action_intent)

        return ActionExecutionResult(
            is_valid=False,
            reason=(
                "Only launch_aircraft, refit_aircraft, return_to_runway, attack_aircraft, and play_operation are executable in this slice."
            ),
            match_state=match_state,
            resolution=None,
            events=[],
            combat_result=None,
        )

    def _execute_attack_aircraft(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        validation = self._validate_attack_aircraft(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
            selected_targets=self._normalized_attack_targets(action_intent),
        )
        if not validation.is_valid:
            return ActionExecutionResult(
                is_valid=False,
                reason=validation.reason,
                match_state=match_state,
                resolution=None,
                combat_result=None,
            )

        target = self._normalized_attack_targets(action_intent)[0]
        attacking_aircraft = self._find_aircraft(
            match_state.get_player(action_intent.player_id),
            action_intent.actor_id,
        )
        target_aircraft = (
            match_state.get_aircraft(target.target_id)
            if target.target_type == AttackTargetType.AIRCRAFT
            else None
        )
        target_player = (
            match_state.get_player(target.target_id)
            if target.target_type == AttackTargetType.RUNWAY
            else None
        )
        tactic_modifiers: list[CombatStatModifier] = collect_tactic_modifiers(
            attacker_id=action_intent.actor_id,
            defender_id=target.target_id if target.target_type == AttackTargetType.AIRCRAFT else None,
            active_buffs=match_state.active_buffs,
        )
        combat_input = build_attack_combat_input(
            action_type=action_intent.action_type,
            actor_player_id=action_intent.player_id,
            attacking_aircraft_id=action_intent.actor_id,
            target_type=target.target_type,
            target_id=target.target_id,
            attacking_aircraft=attacking_aircraft,
            target_aircraft=target_aircraft,
            extra_modifiers=tactic_modifiers,
            die_roll=self._die_roller() if self._die_roller is not None else None,
        )
        combat_result = resolve_attack_combat_result(
            combat_input=combat_input,
            target_aircraft=target_aircraft,
            target_player=target_player,
            match_state=match_state,
        )
        updated_match_state = self._state_updater.consume_buffs_for_aircraft(
            match_state=match_state,
            aircraft_id=action_intent.actor_id,
        )
        if target.target_type == AttackTargetType.AIRCRAFT:
            updated_match_state = self._state_updater.consume_buffs_for_aircraft(
                match_state=updated_match_state,
                aircraft_id=target.target_id,
            )
        updated_match_state = self._state_updater.resolve_attack(
            match_state=updated_match_state,
            player_id=action_intent.player_id,
            attacking_aircraft_id=action_intent.actor_id,
            target_id=target.target_id,
            target_type=target.target_type,
            structure_rating_delta=combat_result.structure_rating_delta,
            runway_damage=combat_result.runway_damage,
        )
        # Apply full-send self-damage: if the attacker had a self_damage buff and the attack hit.
        if combat_result.is_hit:
            self_damage = sum(
                b.self_damage for b in match_state.active_buffs
                if b.aircraft_id == action_intent.actor_id and b.self_damage > 0
            )
            if self_damage > 0:
                updated_match_state = self._state_updater.resolve_attack(
                    match_state=updated_match_state,
                    player_id=action_intent.player_id,
                    attacking_aircraft_id=action_intent.actor_id,
                    target_id=action_intent.actor_id,
                    target_type=AttackTargetType.AIRCRAFT,
                    structure_rating_delta=-self_damage,
                )
        updated_target_aircraft = (
            updated_match_state.get_aircraft(target.target_id)
            if target.target_type == AttackTargetType.AIRCRAFT
            else None
        )
        updated_target_player = (
            updated_match_state.get_player(target.target_id)
            if target.target_type == AttackTargetType.RUNWAY
            else None
        )
        updated_match_state = self._outcome_evaluator.apply_outcome(updated_match_state)
        combat_result = apply_terminal_outcome_to_combat_result(
            combat_result=combat_result,
            match_state=updated_match_state,
        )
        resolution = ActionResolution(
            aircraft_id=action_intent.actor_id,
            action_type=action_intent.action_type,
            previous_zone=Zone.AIR.value,
            current_zone=Zone.AIR.value,
            **combat_result_to_action_resolution_fields(
                combat_result=combat_result,
                updated_target_aircraft=updated_target_aircraft,
                updated_target_player=updated_target_player,
            ),
        )
        events = combat_result_to_events(combat_result=combat_result)
        updated_match_state, events = self._history_manager.append_events(updated_match_state, events)
        return ActionExecutionResult(
            is_valid=True,
            reason=None,
            match_state=updated_match_state,
            resolution=resolution,
            events=events,
            combat_result=combat_result,
        )

    def _execute_return_to_runway(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        validation = self._validate_return_to_runway(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
            selected_target_ids=action_intent.selected_target_ids,
        )
        if not validation.is_valid:
            return ActionExecutionResult(
                is_valid=False,
                reason=validation.reason,
                match_state=match_state,
                resolution=None,
                combat_result=None,
            )

        updated_match_state = self._state_updater.return_to_runway(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
        )
        resolution = ActionResolution(
            aircraft_id=action_intent.actor_id,
            action_type=action_intent.action_type,
            previous_zone=Zone.AIR.value,
            current_zone=Zone.RUNWAY.value,
        )
        events = self._build_standard_action_events(
            actor_player_id=action_intent.player_id,
            resolution=resolution,
        )
        updated_match_state, events = self._history_manager.append_events(updated_match_state, events)
        return ActionExecutionResult(
            is_valid=True,
            reason=None,
            match_state=updated_match_state,
            resolution=resolution,
            events=events,
            combat_result=None,
        )

    def _execute_launch_aircraft(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        validation = self._validate_launch_aircraft(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
            selected_target_ids=action_intent.selected_target_ids,
        )
        if not validation.is_valid:
            return ActionExecutionResult(
                is_valid=False,
                reason=validation.reason,
                match_state=match_state,
                resolution=None,
                combat_result=None,
            )

        updated_match_state = self._state_updater.launch_aircraft(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
        )
        resolution = ActionResolution(
            aircraft_id=action_intent.actor_id,
            action_type=action_intent.action_type,
            previous_zone=Zone.RUNWAY.value,
            current_zone=Zone.AIR.value,
        )
        events = self._build_standard_action_events(
            actor_player_id=action_intent.player_id,
            resolution=resolution,
        )
        updated_match_state, events = self._history_manager.append_events(updated_match_state, events)
        return ActionExecutionResult(
            is_valid=True,
            reason=None,
            match_state=updated_match_state,
            resolution=resolution,
            events=events,
            combat_result=None,
        )

    def _execute_refit_aircraft(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        validation = self._validate_refit_aircraft(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
            selected_target_ids=action_intent.selected_target_ids,
        )
        if not validation.is_valid:
            return ActionExecutionResult(
                is_valid=False,
                reason=validation.reason,
                match_state=match_state,
                resolution=None,
                combat_result=None,
            )

        updated_match_state = self._state_updater.refit_aircraft(
            match_state=match_state,
            player_id=action_intent.player_id,
            aircraft_id=action_intent.actor_id,
        )
        updated_aircraft_state = self._find_aircraft(
            updated_match_state.get_player(action_intent.player_id),
            action_intent.actor_id,
        )
        resolution = ActionResolution(
            aircraft_id=action_intent.actor_id,
            action_type=action_intent.action_type,
            previous_zone=Zone.RUNWAY.value,
            current_zone=Zone.RUNWAY.value,
            fuel=updated_aircraft_state.fuel if updated_aircraft_state is not None else None,
            max_fuel=updated_aircraft_state.max_fuel if updated_aircraft_state is not None else None,
            exhausted=(
                updated_aircraft_state.exhausted
                if updated_aircraft_state is not None
                else None
            ),
            refit_this_turn=(
                updated_aircraft_state.refit_this_turn
                if updated_aircraft_state is not None
                else None
            ),
        )
        events = self._build_standard_action_events(
            actor_player_id=action_intent.player_id,
            resolution=resolution,
        )
        updated_match_state, events = self._history_manager.append_events(updated_match_state, events)
        return ActionExecutionResult(
            is_valid=True,
            reason=None,
            match_state=updated_match_state,
            resolution=resolution,
            events=events,
            combat_result=None,
        )

    def _validate_play_operation(
        self,
        match_state: MatchState,
        player_id: str,
        operation_name: str,
        aircraft_id: str,
    ) -> ActionValidationResult:
        if player_id != match_state.active_player_id:
            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may play operations during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if match_state.phase != Phase.COMMAND:
            return ActionValidationResult(
                is_valid=False,
                reason="Operations may only be played during the command phase.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if operation_name not in OPERATION_CP_COSTS:
            return ActionValidationResult(
                is_valid=False,
                reason=f"Unknown operation: '{operation_name}'.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        cp_cost = OPERATION_CP_COSTS[operation_name]
        player_state = match_state.get_player(player_id)
        if player_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Acting player was not found in this match.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if player_state.command_points < cp_cost:
            return ActionValidationResult(
                is_valid=False,
                reason=f"Not enough command points to play '{operation_name}' (costs {cp_cost}).",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        aircraft_state = self._find_aircraft(player_state, aircraft_id)
        if aircraft_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Target aircraft must belong to the acting player.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )
        if aircraft_state.destroyed:
            return ActionValidationResult(
                is_valid=False,
                reason="Cannot target a destroyed aircraft.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if operation_name == "resupply":
            if aircraft_state.zone != Zone.RUNWAY:
                return ActionValidationResult(
                    is_valid=False,
                    reason="Resupply can only target aircraft on the runway.",
                    legal_actor_ids=[],
                    legal_target_ids=[],
                )

        return ActionValidationResult(
            is_valid=True,
            reason=None,
            legal_actor_ids=[aircraft_id],
            legal_target_ids=[],
        )

    def _execute_play_operation(
        self,
        match_state: MatchState,
        action_intent: ActionIntent,
    ) -> ActionExecutionResult:
        validation = self._validate_play_operation(
            match_state=match_state,
            player_id=action_intent.player_id,
            operation_name=action_intent.operation_name,
            aircraft_id=action_intent.actor_id,
        )
        if not validation.is_valid:
            return ActionExecutionResult(
                is_valid=False,
                reason=validation.reason,
                match_state=match_state,
                resolution=None,
                combat_result=None,
            )

        cp_cost = OPERATION_CP_COSTS[action_intent.operation_name]
        updated_match_state = self._state_updater.decrement_cp(
            match_state=match_state,
            player_id=action_intent.player_id,
            amount=cp_cost,
        )

        if action_intent.operation_name == "resupply":
            updated_match_state = self._state_updater.restore_aircraft_fuel(
                match_state=updated_match_state,
                player_id=action_intent.player_id,
                aircraft_id=action_intent.actor_id,
                amount=RESUPPLY_FUEL_AMOUNT,
            )
        elif action_intent.operation_name in TACTIC_BUFF_DEFINITIONS:
            defn = TACTIC_BUFF_DEFINITIONS[action_intent.operation_name]
            buff = ActiveBuff(
                tactic_id=action_intent.operation_name,
                aircraft_id=action_intent.actor_id,
                player_id=action_intent.player_id,
                attack_delta=defn["attack_delta"],
                evasion_delta=defn["evasion_delta"],
                self_damage=defn["self_damage"],
            )
            updated_match_state = self._state_updater.add_active_buff(updated_match_state, buff)

        player_state = match_state.get_player(action_intent.player_id)
        aircraft_state = self._find_aircraft(player_state, action_intent.actor_id)
        updated_aircraft_state = self._find_aircraft(
            updated_match_state.get_player(action_intent.player_id),
            action_intent.actor_id,
        )

        zone = aircraft_state.zone if aircraft_state is not None else Zone.RUNWAY
        resolution = ActionResolution(
            aircraft_id=action_intent.actor_id,
            action_type=action_intent.action_type,
            previous_zone=zone.value,
            current_zone=zone.value,
            fuel=updated_aircraft_state.fuel if updated_aircraft_state is not None else None,
            max_fuel=updated_aircraft_state.max_fuel if updated_aircraft_state is not None else None,
        )
        events = [
            MatchEvent(
                sequence=0,
                action_type=action_intent.action_type,
                actor_player_id=action_intent.player_id,
                actor_entity_id=action_intent.actor_id,
                outcome_type=f"operation_{action_intent.operation_name}_played",
                from_zone=zone,
                to_zone=zone,
            )
        ]
        updated_match_state, events = self._history_manager.append_events(updated_match_state, events)
        return ActionExecutionResult(
            is_valid=True,
            reason=None,
            match_state=updated_match_state,
            resolution=resolution,
            events=events,
            combat_result=None,
        )

    def _validate_launch_aircraft(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
        selected_target_ids: list[str],
    ) -> ActionValidationResult:
        legal_actor_ids = self._legal_launch_aircraft_ids(match_state, player_id)

        if selected_target_ids:
            return ActionValidationResult(
                is_valid=False,
                reason="launch_aircraft does not accept target selection.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if player_id != match_state.active_player_id:
            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may launch aircraft during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if match_state.phase != Phase.AIR:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft may only launch during the air phase.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Acting player was not found in this match.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        aircraft_state = self._find_aircraft(player_state, aircraft_id)
        if aircraft_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must belong to the acting player.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.destroyed:
            return ActionValidationResult(
                is_valid=False,
                reason="Destroyed aircraft cannot act.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.zone != Zone.RUNWAY:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must be on the runway to launch.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.refit_this_turn:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft that refit this turn cannot launch.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.fuel <= 0:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft does not have enough fuel to launch.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        return ActionValidationResult(
            is_valid=True,
            reason=None,
            legal_actor_ids=legal_actor_ids,
            legal_target_ids=[],
        )

    def _validate_refit_aircraft(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
        selected_target_ids: list[str],
    ) -> ActionValidationResult:
        legal_actor_ids = self._legal_refit_aircraft_ids(match_state, player_id)

        if selected_target_ids:
            return ActionValidationResult(
                is_valid=False,
                reason="refit_aircraft does not accept target selection.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if player_id != match_state.active_player_id:
            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may refit aircraft during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if match_state.phase != Phase.GROUND:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft may only refit during the ground phase.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Acting player was not found in this match.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        aircraft_state = self._find_aircraft(player_state, aircraft_id)
        if aircraft_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must belong to the acting player.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.destroyed:
            return ActionValidationResult(
                is_valid=False,
                reason="Destroyed aircraft cannot act.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.zone != Zone.RUNWAY:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must be on the runway to refit.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        return ActionValidationResult(
            is_valid=True,
            reason=None,
            legal_actor_ids=legal_actor_ids,
            legal_target_ids=[],
        )

    def _validate_return_to_runway(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
        selected_target_ids: list[str],
    ) -> ActionValidationResult:
        legal_actor_ids = self._legal_return_to_runway_ids(match_state, player_id)

        if selected_target_ids:
            return ActionValidationResult(
                is_valid=False,
                reason="return_to_runway does not accept target selection.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if player_id != match_state.active_player_id:
            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may return aircraft to the runway during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if match_state.phase != Phase.AIR:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft may only return to runway during the air phase.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Acting player was not found in this match.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        aircraft_state = self._find_aircraft(player_state, aircraft_id)
        if aircraft_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must belong to the acting player.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.destroyed:
            return ActionValidationResult(
                is_valid=False,
                reason="Destroyed aircraft cannot act.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.zone != Zone.AIR:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft must currently be in the air to return to runway.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        return ActionValidationResult(
            is_valid=True,
            reason=None,
            legal_actor_ids=legal_actor_ids,
            legal_target_ids=[],
        )

    def _validate_attack_aircraft(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
        selected_targets: list[TargetReference],
    ) -> ActionValidationResult:
        legal_actor_ids = self._legal_attack_aircraft_ids(match_state, player_id)

        if player_id != match_state.active_player_id:
            return ActionValidationResult(
                is_valid=False,
                reason="Only the active player may attack during their turn.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        if match_state.phase != Phase.AIR:
            return ActionValidationResult(
                is_valid=False,
                reason="Aircraft may only attack during the air phase.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Acting player was not found in this match.",
                legal_actor_ids=[],
                legal_target_ids=[],
            )

        aircraft_state = self._find_aircraft(player_state, aircraft_id)
        if aircraft_state is None:
            return ActionValidationResult(
                is_valid=False,
                reason="Attacking aircraft must belong to the acting player.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.destroyed:
            return ActionValidationResult(
                is_valid=False,
                reason="Destroyed aircraft cannot act.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.zone != Zone.AIR:
            return ActionValidationResult(
                is_valid=False,
                reason="Attacking aircraft must currently be in the air.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        if aircraft_state.has_attacked_this_phase:
            return ActionValidationResult(
                is_valid=False,
                reason="Attacking aircraft has already attacked this phase.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=[],
            )

        legal_targets = self._legal_attack_targets(match_state, player_id)
        legal_target_ids = [target.target_id for target in legal_targets]

        if len(selected_targets) != 1:
            return ActionValidationResult(
                is_valid=False,
                reason="attack_aircraft requires exactly one target.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=legal_target_ids,
                legal_targets=legal_targets,
            )

        selected_target = selected_targets[0]
        if not any(
            legal_target.target_type == selected_target.target_type
            and legal_target.target_id == selected_target.target_id
            for legal_target in legal_targets
        ):
            return ActionValidationResult(
                is_valid=False,
                reason="Target does not exist or is not a legal attack target.",
                legal_actor_ids=legal_actor_ids,
                legal_target_ids=legal_target_ids,
                legal_targets=legal_targets,
            )

        return ActionValidationResult(
            is_valid=True,
            reason=None,
            legal_actor_ids=legal_actor_ids,
            legal_target_ids=legal_target_ids,
            legal_targets=legal_targets,
        )

    def _legal_launch_aircraft_ids(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> list[str]:
        if player_id != match_state.active_player_id:
            return []
        if match_state.phase != Phase.AIR:
            return []

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return []

        return [
            aircraft.aircraft_id
            for aircraft in player_state.aircraft
            if aircraft.zone == Zone.RUNWAY
            and not aircraft.refit_this_turn
            and not aircraft.destroyed
            and aircraft.fuel > 0
        ]

    def _legal_refit_aircraft_ids(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> list[str]:
        if player_id != match_state.active_player_id:
            return []
        if match_state.phase != Phase.GROUND:
            return []

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return []

        return [
            aircraft.aircraft_id
            for aircraft in player_state.aircraft
            if aircraft.zone == Zone.RUNWAY and not aircraft.destroyed
        ]

    def _legal_return_to_runway_ids(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> list[str]:
        if player_id != match_state.active_player_id:
            return []
        if match_state.phase != Phase.AIR:
            return []

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return []

        return [
            aircraft.aircraft_id
            for aircraft in player_state.aircraft
            if aircraft.zone == Zone.AIR and not aircraft.destroyed
        ]

    def _legal_attack_aircraft_ids(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> list[str]:
        if player_id != match_state.active_player_id:
            return []
        if match_state.phase != Phase.AIR:
            return []

        player_state = match_state.get_player(player_id)
        if player_state is None:
            return []

        return [
            aircraft.aircraft_id
            for aircraft in player_state.aircraft
            if aircraft.zone == Zone.AIR and not aircraft.has_attacked_this_phase and not aircraft.destroyed
        ]

    def _legal_attack_targets(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> list[TargetReference]:
        aircraft_targets = [
            TargetReference(
                target_type=AttackTargetType.AIRCRAFT,
                target_id=aircraft.aircraft_id,
            )
            for player in match_state.players
            if player.player_id != player_id
            for aircraft in player.aircraft
            if aircraft.zone == Zone.AIR and not aircraft.destroyed and not aircraft.exhausted
        ]
        runway_targets = [
            TargetReference(
                target_type=AttackTargetType.RUNWAY,
                target_id=player.player_id,
            )
            for player in match_state.players
            if player.player_id != player_id and player.runway.health > 0
        ]
        return aircraft_targets + runway_targets

    def _normalized_attack_targets(
        self,
        action_intent: ActionIntent,
    ) -> list[TargetReference]:
        if action_intent.selected_targets:
            return action_intent.selected_targets

        return [
            TargetReference(
                target_type=AttackTargetType.AIRCRAFT,
                target_id=target_id,
            )
            for target_id in action_intent.selected_target_ids
        ]

    def _build_standard_action_events(
        self,
        actor_player_id: str,
        resolution: ActionResolution,
    ) -> list[MatchEvent]:
        return [
            MatchEvent(
                sequence=0,
                action_type=resolution.action_type,
                actor_player_id=actor_player_id,
                actor_entity_id=resolution.aircraft_id,
                outcome_type=self._outcome_type_for_resolution(resolution),
                from_zone=Zone(resolution.previous_zone),
                to_zone=Zone(resolution.current_zone),
            )
        ]

    def _outcome_type_for_resolution(self, resolution: ActionResolution) -> str:
        if resolution.action_type == "launch_aircraft":
            return "aircraft_launched"
        if resolution.action_type == "refit_aircraft":
            return "aircraft_refit"
        if resolution.action_type == "return_to_runway":
            return "aircraft_returned_to_runway"
        return resolution.result_type or "action_resolved"

    def _find_aircraft(
        self,
        player_state: PlayerState | None,
        aircraft_id: str,
    ):
        if player_state is None:
            return None
        return next(
            (aircraft for aircraft in player_state.aircraft if aircraft.aircraft_id == aircraft_id),
            None,
        )

    def _legal_targets_for(self, action_intent: ActionIntent) -> list[str]:
        if action_intent.action_type == "play_operation":
            return []
        if action_intent.action_type == "attack":
            return ["opponent-runway", "aircraft-bravo"]
        return []
