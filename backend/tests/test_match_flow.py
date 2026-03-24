from aces_backend.domain.models import AircraftState, MatchState, Phase, Zone
from aces_backend.domain.services import MatchFlow
from helpers import make_match_state


def build_match_state() -> MatchState:
    match_state = make_match_state()
    player_one = match_state.players[0]
    player_one.aircraft.append(
        AircraftState(
            aircraft_id="aircraft-alpha-air",
            owner_player_id="player-1",
            name="Falcon Two",
            fuel=4,
            max_fuel=6,
            structure_rating=3,
            attack=2,
            evasion=3,
            zone=Zone.AIR,
        )
    )
    return match_state


def test_match_flow_advances_through_all_phases_in_order() -> None:
    match_flow = MatchFlow()
    match_state = build_match_state()

    match_state = match_flow.advance_phase(match_state)
    assert match_state.phase == Phase.GROUND
    assert match_state.active_player_id == "player-1"

    match_state = match_flow.advance_phase(match_state)
    assert match_state.phase == Phase.AIR
    assert match_state.active_player_id == "player-1"

    match_state = match_flow.advance_phase(match_state)
    assert match_state.phase == Phase.END
    assert match_state.active_player_id == "player-1"


def test_match_flow_passes_turn_after_end_phase() -> None:
    match_flow = MatchFlow()
    match_state = build_match_state()
    match_state = MatchState(
        match_id=match_state.match_id,
        turn_number=match_state.turn_number,
        active_player_id=match_state.active_player_id,
        phase=Phase.END,
        players=match_state.players,
    )

    next_state = match_flow.advance_phase(match_state)

    assert next_state.phase == Phase.COMMAND
    assert next_state.active_player_id == "player-2"
    assert next_state.turn_number == 1


def test_match_flow_increments_turn_when_rotation_returns_to_first_player() -> None:
    match_flow = MatchFlow()
    match_state = build_match_state()
    match_state = MatchState(
        match_id=match_state.match_id,
        turn_number=1,
        active_player_id="player-2",
        phase=Phase.END,
        players=match_state.players,
    )

    next_state = match_flow.advance_phase(match_state)

    assert next_state.phase == Phase.COMMAND
    assert next_state.active_player_id == "player-1"
    assert next_state.turn_number == 2


def test_player_state_can_filter_aircraft_by_zone() -> None:
    player_state = build_match_state().players[0]

    runway_aircraft = player_state.aircraft_in_zone(Zone.RUNWAY)
    airborne_aircraft = player_state.aircraft_in_zone(Zone.AIR)

    assert [aircraft.aircraft_id for aircraft in runway_aircraft] == ["aircraft-alpha"]
    assert [aircraft.aircraft_id for aircraft in airborne_aircraft] == ["aircraft-alpha-air"]


def test_match_flow_resets_turn_scoped_air_phase_flags_on_turn_handoff() -> None:
    match_flow = MatchFlow()
    match_state = build_match_state()
    match_state.players[0].aircraft[0].has_attacked_this_phase = True
    match_state.players[0].aircraft[0].refit_this_turn = True
    match_state = MatchState(
        match_id=match_state.match_id,
        turn_number=match_state.turn_number,
        active_player_id=match_state.active_player_id,
        phase=Phase.END,
        players=match_state.players,
    )

    next_state = match_flow.advance_phase(match_state)

    assert next_state.phase == Phase.COMMAND
    assert next_state.players[0].aircraft[0].has_attacked_this_phase is False
    assert next_state.players[0].aircraft[0].refit_this_turn is False
