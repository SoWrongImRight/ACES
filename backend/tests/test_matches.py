from aces_backend.api.dependencies import get_match_repository
from aces_backend.domain.models import AttackTargetType, Phase, PilotState, WeaponState, Zone
from aces_backend.rules.engine import ActionIntent, RulesEngine, TargetReference

from helpers import assert_attack_execution_alignment, make_match_state


def create_match(client) -> dict:
    response = client.post("/matches")
    assert response.status_code == 201
    return response.json()


def test_list_matches_is_empty_before_creation(client) -> None:
    response = client.get("/matches")

    assert response.status_code == 200
    assert response.json() == {"matches": []}


def test_create_match_returns_seeded_state_and_persists_it(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    assert payload["match_state"]["match_id"] == match_id
    assert payload["match_state"]["phase"] == "command"
    assert payload["match_state"]["active_player_id"] == "player-1"
    assert payload["match_state"]["is_terminal"] is False
    assert payload["match_state"]["event_history"] == []
    assert payload["match_state"]["players"][0]["runway"]["health"] == 20
    assert payload["match_state"]["players"][0]["aircraft"][0]["zone"] == "runway"
    assert payload["match_state"]["players"][0]["aircraft"][0]["has_attacked_this_phase"] is False
    assert payload["match_state"]["players"][0]["aircraft"][0]["destroyed"] is False

    get_response = client.get(f"/matches/{match_id}")
    assert get_response.status_code == 200
    assert get_response.json()["match_id"] == match_id


def test_get_match_serializes_attachment_state_when_present(client) -> None:
    match_state = make_match_state()
    match_state.players[0].aircraft[0].weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
        exhausted=True,
    )
    match_state.players[0].aircraft[0].pilot = PilotState(
        pilot_id="pilot-1",
        name="Ace",
        attack_bonus=1,
    )
    get_match_repository().save_match(match_state)

    response = client.get("/matches/match-123")

    assert response.status_code == 200
    payload = response.json()
    aircraft = payload["players"][0]["aircraft"][0]
    assert aircraft["weapon"] == {
        "weapon_id": "weapon-1",
        "name": "Cannons",
        "attack_bonus": 2,
        "exhausted": True,
    }
    assert aircraft["pilot"] == {
        "pilot_id": "pilot-1",
        "name": "Ace",
        "attack_bonus": 1,
    }


def test_get_match_returns_not_found_for_unknown_match(client) -> None:
    response = client.get("/matches/missing")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_preview_action_returns_backend_authored_legal_targets_for_attack(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "attack",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    assert response.status_code == 200
    preview_payload = response.json()

    assert preview_payload["status"] == "validated"
    assert preview_payload["is_valid"] is True
    assert preview_payload["legal_actor_ids"] == ["aircraft-alpha"]
    assert preview_payload["legal_target_ids"] == ["opponent-runway", "aircraft-bravo"]


def test_execute_attack_aircraft_succeeds_in_air_phase(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "resolved"
    assert payload["emitted_events"] == [
        {
            "sequence": 1,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "aircraft",
            "target_id": "aircraft-bravo",
            "outcome_type": "hit",
            "from_zone": "air",
            "to_zone": "air",
            "sr_delta": -1,
        }
    ]
    assert payload["action_result"] == {
        "aircraft_id": "aircraft-alpha",
        "action_type": "attack_aircraft",
        "attacking_aircraft_id": "aircraft-alpha",
        "previous_zone": "air",
        "current_zone": "air",
        "target_type": "aircraft",
        "target_id": "aircraft-bravo",
        "executed": True,
        "result_type": "hit",
        "structure_rating_change": -1,
        "target_structure_rating": 3,
        "target_destroyed": False,
    }
    assert payload["match_state"]["players"][0]["aircraft"][0]["has_attacked_this_phase"] is True
    assert payload["match_state"]["event_history"] == payload["emitted_events"]


def test_execute_attack_aircraft_can_miss(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].evasion = 99
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["action_result"]["result_type"] == "miss"
    assert payload["action_result"]["target_type"] == "aircraft"
    assert payload["action_result"]["structure_rating_change"] == 0
    assert payload["action_result"]["target_structure_rating"] == 4
    assert payload["match_state"]["players"][1]["aircraft"][0]["structure_rating"] == 4
    assert payload["match_state"]["players"][0]["aircraft"][0]["has_attacked_this_phase"] is True


def test_execute_attack_aircraft_exhausts_weapon_on_success(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[0].aircraft[0].weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
        exhausted=False,
    )
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    attacking_aircraft = payload["match_state"]["players"][0]["aircraft"][0]
    assert payload["status"] == "resolved"
    assert payload["action_result"]["result_type"] == "hit"
    assert attacking_aircraft["weapon"]["weapon_id"] == "weapon-1"
    assert attacking_aircraft["weapon"]["exhausted"] is True


def test_execute_attack_aircraft_destroys_target_and_sets_terminal_state(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].structure_rating = 1
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["action_result"]["result_type"] == "hit"
    assert payload["action_result"]["target_structure_rating"] == 0
    assert payload["action_result"]["target_destroyed"] is True
    assert payload["match_state"]["players"][1]["aircraft"][0]["destroyed"] is True
    assert payload["match_state"]["is_terminal"] is True
    assert payload["match_state"]["winner_player_id"] == "player-1"
    assert payload["match_state"]["loser_player_id"] == "player-2"
    assert payload["emitted_events"] == [
        {
            "sequence": 1,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "aircraft",
            "target_id": "aircraft-bravo",
            "outcome_type": "hit",
            "from_zone": "air",
            "to_zone": "air",
            "sr_delta": -1,
        },
        {
            "sequence": 2,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "aircraft",
            "target_id": "aircraft-bravo",
            "outcome_type": "entity_destroyed",
            "destroyed_entity_id": "aircraft-bravo",
        },
        {
            "sequence": 3,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "aircraft",
            "target_id": "aircraft-bravo",
            "outcome_type": "match_won",
            "winner_player_id": "player-1",
        },
    ]


def test_preview_action_rejects_non_active_player(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "launch_aircraft",
            "actor_id": "aircraft-bravo",
            "player_id": "player-2",
            "selected_target_ids": [],
        },
    )

    assert response.status_code == 200
    preview_payload = response.json()

    assert preview_payload["status"] == "rejected"
    assert preview_payload["is_valid"] is False
    assert preview_payload["legal_actor_ids"] == []
    assert preview_payload["legal_target_ids"] == []
    assert "active player" in preview_payload["reason"].lower()


def test_advance_phase_requires_active_player(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/advance-phase",
        json={"player_id": "player-2"},
    )

    assert response.status_code == 409
    assert "active player" in response.json()["detail"].lower()


def test_advance_phase_rejects_terminal_match(client) -> None:
    match_state = make_match_state()
    match_state.is_terminal = True
    match_state.winner_player_id = "player-1"
    match_state.loser_player_id = "player-2"
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/advance-phase",
        json={"player_id": "player-1"},
    )

    assert response.status_code == 409
    assert "match is over" in response.json()["detail"].lower()


def test_get_match_still_works_for_terminal_match(client) -> None:
    match_state = make_match_state()
    match_state.is_terminal = True
    match_state.winner_player_id = "player-1"
    match_state.loser_player_id = "player-2"
    get_match_repository().save_match(match_state)

    response = client.get("/matches/match-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_terminal"] is True
    assert payload["winner_player_id"] == "player-1"
    assert payload["loser_player_id"] == "player-2"


def test_advance_phase_moves_match_forward(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    command_to_ground = client.post(
        f"/matches/{match_id}/advance-phase",
        json={"player_id": "player-1"},
    )
    assert command_to_ground.status_code == 200
    assert command_to_ground.json()["match_state"]["phase"] == "ground"

    ground_to_air = client.post(
        f"/matches/{match_id}/advance-phase",
        json={"player_id": "player-1"},
    )
    assert ground_to_air.status_code == 200
    assert ground_to_air.json()["match_state"]["phase"] == "air"


def test_execute_launch_aircraft_succeeds_in_air_phase(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "resolved"
    assert action_payload["action_result"] == {
        "aircraft_id": "aircraft-alpha",
        "previous_zone": "runway",
        "current_zone": "air",
    }
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["zone"] == "air"


def test_execute_refit_aircraft_succeeds_in_ground_phase(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    repository = get_match_repository()
    match_state = repository.get_match(match_id)
    assert match_state is not None
    match_state.players[0].aircraft[0].fuel = 1
    match_state.players[0].aircraft[0].exhausted = True
    repository.save_match(match_state)

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "resolved"
    assert action_payload["action_result"] == {
        "aircraft_id": "aircraft-alpha",
        "previous_zone": "runway",
        "current_zone": "runway",
        "fuel": 6,
        "max_fuel": 6,
        "exhausted": False,
        "refit_this_turn": True,
    }
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["fuel"] == 6
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["exhausted"] is False
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["refit_this_turn"] is True


def test_execute_refit_aircraft_clears_weapon_exhaustion(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    repository = get_match_repository()
    match_state = repository.get_match(match_id)
    assert match_state is not None
    match_state.players[0].aircraft[0].weapon = WeaponState(
        weapon_id="weapon-1",
        name="Cannons",
        attack_bonus=2,
        exhausted=True,
    )
    repository.save_match(match_state)

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()
    aircraft = action_payload["match_state"]["players"][0]["aircraft"][0]
    assert action_payload["status"] == "resolved"
    assert aircraft["weapon"]["weapon_id"] == "weapon-1"
    assert aircraft["weapon"]["exhausted"] is False


def test_execute_return_to_runway_succeeds_in_air_phase(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "resolved"
    assert action_payload["action_result"] == {
        "aircraft_id": "aircraft-alpha",
        "previous_zone": "air",
        "current_zone": "runway",
    }
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["zone"] == "runway"


def test_execute_launch_aircraft_rejects_non_active_player(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-2",
            "aircraft_id": "aircraft-bravo",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "active player" in action_payload["reason"].lower()


def test_execute_attack_aircraft_rejects_non_active_player(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-2",
            "attacking_aircraft_id": "aircraft-bravo",
            "target": {"target_type": "aircraft", "target_id": "aircraft-alpha"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "active player" in payload["reason"].lower()


def test_execute_return_to_runway_rejects_non_active_player(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-2",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "active player" in action_payload["reason"].lower()


def test_execute_refit_aircraft_rejects_non_active_player(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-2",
            "aircraft_id": "aircraft-bravo",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "active player" in action_payload["reason"].lower()


def test_execute_return_to_runway_rejects_when_aircraft_does_not_belong_to_player(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-bravo",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "belong" in action_payload["reason"].lower()


def test_execute_attack_aircraft_rejects_when_attacker_does_not_belong_to_player(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-bravo",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "belong" in payload["reason"].lower()


def test_execute_launch_aircraft_rejects_when_aircraft_is_not_on_runway(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "runway" in action_payload["reason"].lower()


def test_execute_return_to_runway_rejects_when_aircraft_is_already_on_runway(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "in the air" in action_payload["reason"].lower()


def test_execute_attack_aircraft_rejects_when_attacker_is_not_in_air(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "in the air" in payload["reason"].lower()


def test_execute_refit_aircraft_rejects_when_aircraft_is_not_on_runway(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.GROUND
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "runway" in action_payload["reason"].lower()


def test_execute_return_to_runway_rejects_when_phase_is_not_air(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "air phase" in action_payload["reason"].lower()


def test_execute_attack_aircraft_rejects_when_has_attacked_this_phase_is_true(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[0].aircraft[0].has_attacked_this_phase = True
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "already attacked" in payload["reason"].lower()


def test_execute_attack_aircraft_rejects_when_target_does_not_exist(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "missing-aircraft"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "target" in payload["reason"].lower()


def test_destroyed_aircraft_are_not_legal_actors_or_targets(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[0].aircraft[0].destroyed = True
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].destroyed = True
    get_match_repository().save_match(match_state)

    actor_preview = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "attack_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_targets": [{"target_type": "aircraft", "target_id": "aircraft-bravo"}],
        },
    )

    target_preview = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "attack_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_targets": [{"target_type": "aircraft", "target_id": "aircraft-bravo"}],
        },
    )

    assert actor_preview.status_code == 200
    assert target_preview.status_code == 200
    assert actor_preview.json()["status"] == "rejected"
    assert "destroyed" in actor_preview.json()["reason"].lower()
    assert target_preview.json()["legal_target_ids"] == []


def test_execute_refit_aircraft_rejects_when_phase_is_not_ground(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert response.status_code == 200
    action_payload = response.json()

    assert action_payload["status"] == "rejected"
    assert "ground phase" in action_payload["reason"].lower()


def test_execute_launch_aircraft_rejects_when_aircraft_refit_this_turn(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].refit_this_turn = True
    get_match_repository().save_match(match_state)

    preview_response = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "launch_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    execute_response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert "refit" in preview_response.json()["reason"].lower()
    assert "refit" in execute_response.json()["reason"].lower()


def test_launch_is_rejected_after_refit_in_same_turn(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    refit_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    phase_response = client.post(
        f"/matches/{match_id}/advance-phase",
        json={"player_id": "player-1"},
    )

    preview_response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "launch_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    execute_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert refit_response.status_code == 200
    assert phase_response.status_code == 200
    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["status"] == "rejected"
    assert execute_response.json()["status"] == "rejected"
    assert "refit" in preview_response.json()["reason"].lower()
    assert "refit" in execute_response.json()["reason"].lower()


def test_preview_launch_aircraft_matches_execution_legality(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    preview_response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "launch_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    execute_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["is_valid"] is True
    assert preview_response.json()["legal_actor_ids"] == ["aircraft-alpha"]
    assert execute_response.json()["status"] == "resolved"


def test_preview_refit_aircraft_matches_execution_legality(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    preview_response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "refit_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    execute_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["is_valid"] is True
    assert preview_response.json()["legal_actor_ids"] == ["aircraft-alpha"]
    assert execute_response.json()["status"] == "resolved"


def test_preview_return_to_runway_matches_execution_legality(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    preview_response = client.post(
        f"/matches/{match_id}/actions/preview",
        json={
            "action_type": "return_to_runway",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_target_ids": [],
        },
    )

    execute_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["is_valid"] is True
    assert preview_response.json()["legal_actor_ids"] == ["aircraft-alpha"]
    assert execute_response.json()["status"] == "resolved"


def test_preview_attack_aircraft_matches_execution_legality(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    preview_response = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "attack_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_targets": [{"target_type": "aircraft", "target_id": "aircraft-bravo"}],
        },
    )

    execute_response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["is_valid"] is True
    assert preview_response.json()["legal_actor_ids"] == ["aircraft-alpha"]
    assert preview_response.json()["legal_target_ids"] == ["aircraft-bravo", "player-2"]
    assert preview_response.json()["legal_targets"] == [
        {"target_type": "aircraft", "target_id": "aircraft-bravo"},
        {"target_type": "runway", "target_id": "player-2"},
    ]
    assert execute_response.json()["status"] == "resolved"


def test_execute_attack_aircraft_can_target_enemy_runway(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "runway", "target_id": "player-2"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["action_result"]["target_type"] == "runway"
    assert payload["action_result"]["target_id"] == "player-2"
    assert payload["action_result"]["result_type"] == "runway_hit"
    assert payload["action_result"]["runway_health_change"] == -1
    assert payload["action_result"]["target_runway_health"] == 19
    assert payload["action_result"]["target_destroyed"] is False
    assert payload["match_state"]["players"][1]["runway"]["health"] == 19
    assert payload["match_state"]["players"][0]["aircraft"][0]["has_attacked_this_phase"] is True
    assert payload["emitted_events"] == [
        {
            "sequence": 1,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "runway",
            "target_id": "player-2",
            "outcome_type": "runway_hit",
            "from_zone": "air",
            "to_zone": "air",
            "runway_damage": 1,
        }
    ]


def test_execute_attack_aircraft_rejects_own_runway_target(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "runway", "target_id": "player-1"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "rejected"
    assert "target" in payload["reason"].lower()


def test_execute_attack_aircraft_destroying_runway_sets_terminal_state(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].runway.health = 1
    get_match_repository().save_match(match_state)

    response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "runway", "target_id": "player-2"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert payload["action_result"]["target_runway_health"] == 0
    assert payload["action_result"]["target_destroyed"] is True
    assert payload["match_state"]["players"][1]["runway"]["health"] == 0
    assert payload["match_state"]["is_terminal"] is True
    assert payload["match_state"]["winner_player_id"] == "player-1"
    assert payload["match_state"]["loser_player_id"] == "player-2"
    assert payload["emitted_events"] == [
        {
            "sequence": 1,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "runway",
            "target_id": "player-2",
            "outcome_type": "runway_hit",
            "from_zone": "air",
            "to_zone": "air",
            "runway_damage": 1,
        },
        {
            "sequence": 2,
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "target_type": "runway",
            "target_id": "player-2",
            "outcome_type": "match_won",
            "winner_player_id": "player-1",
        },
    ]


def test_preview_attack_runway_matches_execution_legality(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    get_match_repository().save_match(match_state)

    preview_response = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "attack_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_targets": [{"target_type": "runway", "target_id": "player-2"}],
        },
    )

    execute_response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "attack_aircraft",
            "actor_player_id": "player-1",
            "attacking_aircraft_id": "aircraft-alpha",
            "target": {"target_type": "runway", "target_id": "player-2"},
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["is_valid"] is True
    assert {"target_type": "runway", "target_id": "player-2"} in preview_response.json()[
        "legal_targets"
    ]
    assert execute_response.json()["status"] == "resolved"


def test_no_further_actions_are_accepted_once_match_is_terminal(client) -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].destroyed = True
    match_state.is_terminal = True
    match_state.winner_player_id = "player-1"
    match_state.loser_player_id = "player-2"
    get_match_repository().save_match(match_state)

    preview_response = client.post(
        "/matches/match-123/actions/preview",
        json={
            "action_type": "attack_aircraft",
            "actor_id": "aircraft-alpha",
            "player_id": "player-1",
            "selected_targets": [{"target_type": "aircraft", "target_id": "aircraft-bravo"}],
        },
    )
    execute_response = client.post(
        "/matches/match-123/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert preview_response.status_code == 200
    assert execute_response.status_code == 200
    assert preview_response.json()["status"] == "rejected"
    assert execute_response.json()["status"] == "rejected"
    assert "already over" in preview_response.json()["reason"].lower()
    assert "already over" in execute_response.json()["reason"].lower()
    assert execute_response.json()["emitted_events"] == []


def test_launch_and_return_events_are_recorded_in_deterministic_order(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    launch_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )
    return_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "return_to_runway",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )
    match_response = client.get(f"/matches/{match_id}")

    assert launch_response.status_code == 200
    assert return_response.status_code == 200
    assert match_response.status_code == 200
    assert launch_response.json()["emitted_events"] == [
        {
            "sequence": 1,
            "action_type": "launch_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "outcome_type": "aircraft_launched",
            "from_zone": "runway",
            "to_zone": "air",
        }
    ]
    assert return_response.json()["emitted_events"] == [
        {
            "sequence": 2,
            "action_type": "return_to_runway",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "outcome_type": "aircraft_returned_to_runway",
            "from_zone": "air",
            "to_zone": "runway",
        }
    ]
    assert match_response.json()["event_history"] == [
        {
            "sequence": 1,
            "action_type": "launch_aircraft",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "outcome_type": "aircraft_launched",
            "from_zone": "runway",
            "to_zone": "air",
        },
        {
            "sequence": 2,
            "action_type": "return_to_runway",
            "actor_player_id": "player-1",
            "actor_entity_id": "aircraft-alpha",
            "outcome_type": "aircraft_returned_to_runway",
            "from_zone": "air",
            "to_zone": "runway",
        },
    ]


def test_rejected_actions_do_not_append_success_history(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "launch_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )
    match_response = client.get(f"/matches/{match_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["emitted_events"] == []
    assert match_response.status_code == 200
    assert match_response.json()["event_history"] == []


def test_combat_result_for_aircraft_attack_aligns_with_emitted_events() -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR

    result = RulesEngine().execute_action(
        match_state,
        ActionIntent(
            action_type="attack_aircraft",
            actor_id="aircraft-alpha",
            player_id="player-1",
            selected_target_ids=["aircraft-bravo"],
        ),
    )

    combat_result = assert_attack_execution_alignment(
        result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
    )
    assert combat_result.attacking_aircraft_id == "aircraft-alpha"


def test_combat_result_for_runway_attack_aligns_with_emitted_events() -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR

    result = RulesEngine().execute_action(
        match_state,
        ActionIntent(
            action_type="attack_aircraft",
            actor_id="aircraft-alpha",
            player_id="player-1",
            selected_targets=[
                TargetReference(target_type=AttackTargetType.RUNWAY, target_id="player-2")
            ],
        ),
    )

    combat_result = assert_attack_execution_alignment(
        result,
        expected_outcome_type="runway_hit",
        expected_target_id="player-2",
        expected_runway_damage=1,
    )
    assert combat_result.attacking_aircraft_id == "aircraft-alpha"


def test_combat_result_destruction_and_terminal_win_stay_aligned() -> None:
    match_state = make_match_state()
    match_state.phase = Phase.AIR
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].zone = Zone.AIR
    match_state.players[1].aircraft[0].structure_rating = 1

    result = RulesEngine().execute_action(
        match_state,
        ActionIntent(
            action_type="attack_aircraft",
            actor_id="aircraft-alpha",
            player_id="player-1",
            selected_target_ids=["aircraft-bravo"],
        ),
    )

    combat_result = assert_attack_execution_alignment(
        result,
        expected_outcome_type="hit",
        expected_target_id="aircraft-bravo",
        expected_sr_delta=-1,
        expected_destroyed_entity_id="aircraft-bravo",
        expected_winner_player_id="player-1",
    )
    assert result.match_state.players[1].aircraft[0].destroyed is True
    assert result.match_state.winner_player_id == combat_result.winner_player_id
    assert result.events[1].destroyed_entity_id == combat_result.destroyed_entity_id
    assert result.events[2].winner_player_id == combat_result.winner_player_id


def test_illegal_attack_does_not_produce_combat_result_or_events() -> None:
    match_state = make_match_state()

    result = RulesEngine().execute_action(
        match_state,
        ActionIntent(
            action_type="attack_aircraft",
            actor_id="aircraft-alpha",
            player_id="player-1",
            selected_target_ids=["aircraft-bravo"],
        ),
    )

    assert result.is_valid is False
    assert result.combat_result is None
    assert result.events == []


def test_refit_clears_exhaustion_state(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    repository = get_match_repository()
    match_state = repository.get_match(match_id)
    assert match_state is not None
    match_state.players[0].aircraft[0].exhausted = True
    match_state.players[0].aircraft[0].fuel = 2
    repository.save_match(match_state)

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    execute_response = client.post(
        f"/matches/{match_id}/actions",
        json={
            "action_type": "refit_aircraft",
            "player_id": "player-1",
            "aircraft_id": "aircraft-alpha",
        },
    )

    assert execute_response.status_code == 200
    action_payload = execute_response.json()
    assert action_payload["status"] == "resolved"
    assert action_payload["action_result"]["exhausted"] is False
    assert action_payload["match_state"]["players"][0]["aircraft"][0]["exhausted"] is False


def test_has_attacked_this_phase_serializes_in_match_state(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    repository = get_match_repository()
    match_state = repository.get_match(match_id)
    assert match_state is not None
    match_state.players[0].aircraft[0].has_attacked_this_phase = True
    repository.save_match(match_state)

    response = client.get(f"/matches/{match_id}")

    assert response.status_code == 200
    assert response.json()["players"][0]["aircraft"][0]["has_attacked_this_phase"] is True


def test_turn_handoff_resets_has_attacked_this_phase_without_breaking_actions(client) -> None:
    payload = create_match(client)
    match_id = payload["match_id"]

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})
    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    repository = get_match_repository()
    match_state = repository.get_match(match_id)
    assert match_state is not None
    match_state.players[0].aircraft[0].zone = Zone.AIR
    match_state.players[0].aircraft[0].has_attacked_this_phase = True
    repository.save_match(match_state)

    client.post(f"/matches/{match_id}/advance-phase", json={"player_id": "player-1"})

    next_turn_state = client.post(
        f"/matches/{match_id}/advance-phase",
        json={"player_id": "player-1"},
    )

    assert next_turn_state.status_code == 200
    next_payload = next_turn_state.json()
    assert next_payload["match_state"]["active_player_id"] == "player-2"
    assert next_payload["match_state"]["players"][0]["aircraft"][0]["has_attacked_this_phase"] is False
