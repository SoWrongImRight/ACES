from aces_backend.domain.models import AttackTargetType, PilotState, WeaponState
from aces_backend.rules.combat import (
    COMBAT_MODIFIER_CATEGORY_ORDER,
    CombatModifierCategory,
    CombatStatModifier,
    CombatInputBuilder,
    apply_terminal_outcome_to_combat_result,
    build_attack_combat_input,
    collect_attachment_attack_modifiers,
    collect_pilot_attack_modifiers,
    collect_weapon_attack_modifiers,
    combat_result_to_action_resolution_fields,
    combat_result_to_events,
    order_combat_modifiers,
    resolve_attack_combat_result,
)

from helpers import (
    assert_combat_input_snapshot,
    assert_combat_result_snapshot,
    make_match_state,
)


def test_builder_produces_expected_combat_input_for_aircraft_target() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )

    assert_combat_input_snapshot(
        combat_input,
        expected_target_id="aircraft-bravo",
        expected_base_attack=3,
        expected_base_evasion=3,
        expected_resolved_attack=3,
        expected_resolved_evasion=3,
    )


def test_builder_output_with_no_modifiers_remains_unchanged() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )

    assert_combat_input_snapshot(
        combat_input,
        expected_target_id="aircraft-bravo",
        expected_base_attack=3,
        expected_base_evasion=3,
        expected_resolved_attack=3,
        expected_resolved_evasion=3,
    )


def test_builder_produces_expected_combat_input_for_runway_target() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]

    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.RUNWAY,
        target_id="player-2",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=None,
    )

    assert_combat_input_snapshot(
        combat_input,
        expected_target_id="player-2",
        expected_base_attack=3,
        expected_base_evasion=None,
        expected_resolved_attack=3,
        expected_resolved_evasion=None,
    )


def test_ordered_modifier_application_adjusts_resolved_values_predictably() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
        extra_modifiers=[
            CombatStatModifier(
                category=CombatModifierCategory.TEMPORARY_EFFECT,
                source="training",
                attack_delta=2,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.TEMPORARY_EFFECT,
                source="weather",
                evasion_delta=1,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.HAZARD_DEBUFF,
                source="drag",
                attack_delta=-1,
                evasion_delta=-2,
            ),
        ],
    )

    assert_combat_input_snapshot(
        combat_input,
        expected_target_id="aircraft-bravo",
        expected_base_attack=3,
        expected_base_evasion=3,
        expected_resolved_attack=4,
        expected_resolved_evasion=2,
    )


def test_builder_output_produces_same_aircraft_attack_result() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
    )


def test_resolver_behavior_stays_aligned_when_fed_modified_combat_input() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    target_aircraft.evasion = 5
    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
        extra_modifiers=[
            CombatStatModifier(
                category=CombatModifierCategory.TEMPORARY_EFFECT,
                source="support",
                attack_delta=-1,
            )
        ],
        die_roll=1,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.resolved_attack == 2
    assert combat_input.resolved_evasion == 5
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="miss",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=0,
    )


def test_builder_output_produces_same_runway_attack_result() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_player = match_state.players[1]

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.RUNWAY,
        target_id="player-2",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=None,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=None,
        target_player=target_player,
        match_state=match_state,
    )

    assert combat_input.base_attack == 3
    assert combat_input.base_evasion is None
    assert combat_input.resolved_evasion is None
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="runway_hit",
        expected_target_id="player-2",
        expected_runway_damage=1,
    )


def test_combat_result_event_translation_stays_aligned() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    target_aircraft.structure_rating = 1

    combat_result = resolve_attack_combat_result(
        combat_input=build_attack_combat_input(
            action_type="attack_aircraft",
            actor_player_id="player-1",
            attacking_aircraft_id="aircraft-alpha",
            target_type=AttackTargetType.AIRCRAFT,
            target_id="aircraft-bravo",
            attacking_aircraft=attacking_aircraft,
            target_aircraft=target_aircraft,
        ),
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )
    terminal_match_state = make_match_state()
    terminal_match_state.is_terminal = True
    terminal_match_state.winner_player_id = "player-1"
    combat_result = apply_terminal_outcome_to_combat_result(
        combat_result=combat_result,
        match_state=terminal_match_state,
    )
    events = combat_result_to_events(combat_result=combat_result)

    assert events[0].outcome_type == combat_result.outcome_type
    assert events[0].target_id == combat_result.target_id
    assert events[0].sr_delta == combat_result.structure_rating_delta
    assert events[-1].winner_player_id == combat_result.winner_player_id


def test_combat_result_response_field_translation_stays_aligned() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_player = match_state.players[1]

    combat_result = resolve_attack_combat_result(
        combat_input=build_attack_combat_input(
            action_type="attack_aircraft",
            actor_player_id="player-1",
            attacking_aircraft_id="aircraft-alpha",
            target_type=AttackTargetType.RUNWAY,
            target_id="player-2",
            attacking_aircraft=attacking_aircraft,
            target_aircraft=None,
        ),
        target_aircraft=None,
        target_player=target_player,
        match_state=match_state,
    )
    fields = combat_result_to_action_resolution_fields(
        combat_result=combat_result,
        updated_target_aircraft=None,
        updated_target_player=target_player,
    )

    assert fields["result_type"] == combat_result.outcome_type
    assert fields["target_id"] == combat_result.target_id
    assert fields["runway_health_change"] == -1
    assert fields["target_destroyed"] is False


def test_aircraft_with_no_weapon_behaves_as_before() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    target_aircraft.evasion = 5

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
        die_roll=1,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.resolved_attack == 3
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="miss",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=0,
    )


def test_pilot_contribution_helper_outputs_expected_modifier() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    attacking_aircraft.pilot = PilotState(
        pilot_id="pilot-1",
        name="Ace",
        attack_bonus=1,
    )

    modifiers = collect_pilot_attack_modifiers(attacking_aircraft=attacking_aircraft)

    assert modifiers == [
        CombatStatModifier(
            category=CombatModifierCategory.PILOT,
            source="pilot:pilot-1",
            attack_delta=1,
        )
    ]


def test_aircraft_with_weapon_gets_expected_attack_contribution() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    attacking_aircraft.weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
    )
    target_aircraft.evasion = 4

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.base_attack == 3
    assert combat_input.resolved_attack == 5
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
    )
    events = combat_result_to_events(combat_result=combat_result)
    fields = combat_result_to_action_resolution_fields(
        combat_result=combat_result,
        updated_target_aircraft=target_aircraft,
        updated_target_player=None,
    )
    assert events[0].outcome_type == combat_result.outcome_type
    assert fields["result_type"] == combat_result.outcome_type


def test_weapon_contribution_helper_outputs_expected_modifier() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    attacking_aircraft.weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
    )

    modifiers = collect_weapon_attack_modifiers(attacking_aircraft=attacking_aircraft)

    assert modifiers == [
        CombatStatModifier(
            category=CombatModifierCategory.WEAPON,
            source="weapon:weapon-1",
            attack_delta=2,
        )
    ]


def test_exhausted_weapon_does_not_contribute_attack_bonus() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    attacking_aircraft.weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
        exhausted=True,
    )
    target_aircraft.evasion = 5

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
        die_roll=1,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.base_attack == 3
    assert combat_input.resolved_attack == 3
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="miss",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=0,
    )


def test_attachment_modifier_collection_preserves_deterministic_order() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    attacking_aircraft.pilot = PilotState(
        pilot_id="pilot-1",
        name="Ace",
        attack_bonus=1,
    )
    attacking_aircraft.weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
    )

    modifiers = collect_attachment_attack_modifiers(attacking_aircraft=attacking_aircraft)

    assert modifiers == [
        CombatStatModifier(
            category=CombatModifierCategory.PILOT,
            source="pilot:pilot-1",
            attack_delta=1,
        ),
        CombatStatModifier(
            category=CombatModifierCategory.WEAPON,
            source="weapon:weapon-1",
            attack_delta=2,
        ),
    ]


def test_modifier_category_order_convention_is_explicit_and_stable() -> None:
    assert COMBAT_MODIFIER_CATEGORY_ORDER == (
        CombatModifierCategory.PILOT,
        CombatModifierCategory.WEAPON,
        CombatModifierCategory.AIRFRAME,
        CombatModifierCategory.TEMPORARY_EFFECT,
        CombatModifierCategory.HAZARD_DEBUFF,
    )


def test_modifier_ordering_remains_deterministic_under_category_convention() -> None:
    ordered = order_combat_modifiers(
        [
            CombatStatModifier(
                category=CombatModifierCategory.HAZARD_DEBUFF,
                source="hazard",
                attack_delta=-1,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.WEAPON,
                source="weapon:weapon-1",
                attack_delta=2,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.PILOT,
                source="pilot:pilot-1",
                attack_delta=1,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.AIRFRAME,
                source="airframe:mod-1",
                evasion_delta=1,
            ),
        ]
    )

    assert [modifier.category for modifier in ordered] == [
        CombatModifierCategory.PILOT,
        CombatModifierCategory.WEAPON,
        CombatModifierCategory.AIRFRAME,
        CombatModifierCategory.HAZARD_DEBUFF,
    ]


def test_future_empty_categories_do_not_affect_current_builder_results() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]

    combat_input = CombatInputBuilder().build_attack_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
        extra_modifiers=[
            CombatStatModifier(
                category=CombatModifierCategory.AIRFRAME,
                source="airframe:none",
                attack_delta=0,
                evasion_delta=0,
            ),
            CombatStatModifier(
                category=CombatModifierCategory.TEMPORARY_EFFECT,
                source="temporary:none",
                attack_delta=0,
                evasion_delta=0,
            ),
        ],
    )

    assert_combat_input_snapshot(
        combat_input,
        expected_target_id="aircraft-bravo",
        expected_base_attack=3,
        expected_base_evasion=3,
        expected_resolved_attack=3,
        expected_resolved_evasion=3,
    )


def test_pilotless_aircraft_behaves_as_before() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    target_aircraft.evasion = 4

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )

    assert combat_input.resolved_attack == 3


def test_pilot_contribution_changes_resolved_values_predictably() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    attacking_aircraft.pilot = PilotState(
        pilot_id="pilot-1",
        name="Ace",
        attack_bonus=1,
    )
    target_aircraft.evasion = 4

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.resolved_attack == 4
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
    )


def test_pilot_and_weapon_contributions_can_coexist_deterministically() -> None:
    match_state = make_match_state()
    attacking_aircraft = match_state.players[0].aircraft[0]
    target_aircraft = match_state.players[1].aircraft[0]
    attacking_aircraft.pilot = PilotState(
        pilot_id="pilot-1",
        name="Ace",
        attack_bonus=1,
    )
    attacking_aircraft.weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
    )
    target_aircraft.evasion = 6

    combat_input = build_attack_combat_input(
        action_type="attack_aircraft",
        actor_player_id="player-1",
        attacking_aircraft_id="aircraft-alpha",
        target_type=AttackTargetType.AIRCRAFT,
        target_id="aircraft-bravo",
        attacking_aircraft=attacking_aircraft,
        target_aircraft=target_aircraft,
    )
    combat_result = resolve_attack_combat_result(
        combat_input=combat_input,
        target_aircraft=target_aircraft,
        target_player=None,
        match_state=match_state,
    )

    assert combat_input.base_attack == 3
    assert combat_input.resolved_attack == 6
    assert_combat_result_snapshot(
        combat_result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
    )
