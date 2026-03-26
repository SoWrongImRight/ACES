from aces_backend.domain.factory import build_seeded_match
from aces_backend.domain.models import MatchState
from aces_backend.rules.combat import CombatInput, CombatResult
from aces_backend.rules.engine import ActionExecutionResult


def make_match_state(match_id: str = "match-123") -> MatchState:
    match_state = build_seeded_match(match_id=match_id)
    for player in match_state.players:
        for aircraft in player.aircraft:
            aircraft.weapon = None
            aircraft.pilot = None
    return match_state


def assert_combat_result_snapshot(
    combat_result: CombatResult,
    *,
    expected_outcome_type: str,
    expected_target_id: str,
    expected_sr_delta: int = 0,
    expected_runway_damage: int = 0,
    expected_destroyed_entity_id: str | None = None,
    expected_winner_player_id: str | None = None,
) -> CombatResult:
    assert combat_result.outcome_type == expected_outcome_type
    assert combat_result.target_id == expected_target_id
    assert combat_result.structure_rating_delta == expected_sr_delta
    assert combat_result.runway_damage == expected_runway_damage
    assert combat_result.destroyed_entity_id == expected_destroyed_entity_id
    assert combat_result.winner_player_id == expected_winner_player_id
    return combat_result


def assert_combat_input_snapshot(
    combat_input: CombatInput,
    *,
    expected_target_id: str,
    expected_base_attack: int,
    expected_base_evasion: int | None,
    expected_resolved_attack: int,
    expected_resolved_evasion: int | None,
) -> CombatInput:
    assert combat_input.target_id == expected_target_id
    assert combat_input.base_attack == expected_base_attack
    assert combat_input.base_evasion == expected_base_evasion
    assert combat_input.resolved_attack == expected_resolved_attack
    assert combat_input.resolved_evasion == expected_resolved_evasion
    return combat_input


def assert_attack_execution_alignment(
    result: ActionExecutionResult,
    *,
    expected_outcome_type: str,
    expected_target_id: str,
    expected_sr_delta: int = 0,
    expected_runway_damage: int = 0,
    expected_destroyed_entity_id: str | None = None,
    expected_winner_player_id: str | None = None,
) -> CombatResult:
    assert result.is_valid is True
    assert result.combat_result is not None

    combat_result = assert_combat_result_snapshot(
        result.combat_result,
        expected_outcome_type=expected_outcome_type,
        expected_target_id=expected_target_id,
        expected_sr_delta=expected_sr_delta,
        expected_runway_damage=expected_runway_damage,
        expected_destroyed_entity_id=expected_destroyed_entity_id,
        expected_winner_player_id=expected_winner_player_id,
    )
    assert result.events[0].outcome_type == combat_result.outcome_type
    assert result.events[0].target_id == combat_result.target_id
    assert result.events[0].sr_delta == (
        expected_sr_delta if combat_result.target_type.value == "aircraft" else None
    )
    assert result.events[0].runway_damage == (
        expected_runway_damage if combat_result.target_type.value == "runway" else None
    )
    return combat_result
