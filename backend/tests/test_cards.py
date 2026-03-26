from pathlib import Path

from aces_backend.cards.loader import CardLoader
from aces_backend.cards.source import LocalFileCardSource

# Resolve the cards directory relative to this test file.
# tests/ -> backend/ -> aces/ -> cards/
_CARDS_DIR = Path(__file__).resolve().parents[2] / "cards"


def make_loader() -> CardLoader:
    return CardLoader(LocalFileCardSource(_CARDS_DIR))


def test_base_set_is_discoverable() -> None:
    assert "base-set" in LocalFileCardSource(_CARDS_DIR).list_sets()


def test_loader_loads_all_aircraft_from_base_set() -> None:
    ids = [a.card_id for a in make_loader().load_aircraft()]
    assert "falcon-one" in ids
    assert "eagle-three" in ids
    assert "viper-two" in ids
    assert "hawk-four" in ids
    assert "raven-five" in ids
    assert "thunder-six" in ids


def test_loader_loads_all_weapons_from_base_set() -> None:
    ids = [w.card_id for w in make_loader().load_weapons()]
    assert "20mm-cannon" in ids
    assert "sidewinder-missile" in ids
    assert "heavy-cannon" in ids
    assert "long-range-missile" in ids
    assert "rocket-pod" in ids


def test_loader_loads_all_pilots_from_base_set() -> None:
    ids = [p.card_id for p in make_loader().load_pilots()]
    assert "maverick" in ids
    assert "ghost" in ids
    assert "viper" in ids
    assert "bandit" in ids
    assert "ace" in ids


def test_loader_loads_all_tactics_from_base_set() -> None:
    ids = [t.card_id for t in make_loader().load_tactics()]
    assert "afterburner" in ids
    assert "target-lock" in ids
    assert "full-send" in ids
    assert "fuel-conserve" in ids
    assert "evasive-maneuvers" in ids


def test_loader_loads_all_hazards_from_base_set() -> None:
    ids = [h.card_id for h in make_loader().load_hazards()]
    assert "flak-burst" in ids
    assert "missile-jam" in ids
    assert "fuel-leak" in ids
    assert "stall-out" in ids
    assert "structural-hit" in ids
    assert "radar-spoof" in ids
    assert "crosswind" in ids


def test_find_aircraft_returns_correct_stats() -> None:
    card = make_loader().find_aircraft("falcon-one")
    assert card is not None
    assert card.name == "Falcon One"
    assert card.attack == 3
    assert card.evasion == 4
    assert card.structure_rating == 4
    assert card.max_fuel == 6


def test_find_weapon_returns_correct_stats() -> None:
    card = make_loader().find_weapon("sidewinder-missile")
    assert card is not None
    assert card.attack_bonus == 2
    assert card.damage == 3


def test_find_pilot_attack_only_bonus() -> None:
    card = make_loader().find_pilot("maverick")
    assert card is not None
    assert card.attack_bonus == 1
    assert card.evasion_bonus == 0
    assert card.fuel_bonus == 0
    assert card.structure_bonus == 0


def test_find_pilot_evasion_bonus() -> None:
    card = make_loader().find_pilot("ghost")
    assert card is not None
    assert card.evasion_bonus == 1
    assert card.attack_bonus == 0


def test_find_pilot_fuel_bonus() -> None:
    card = make_loader().find_pilot("viper")
    assert card is not None
    assert card.fuel_bonus == 1
    assert card.attack_bonus == 0


def test_find_pilot_structure_bonus() -> None:
    card = make_loader().find_pilot("bandit")
    assert card is not None
    assert card.structure_bonus == 1
    assert card.attack_bonus == 0


def test_find_pilot_multi_bonus() -> None:
    card = make_loader().find_pilot("ace")
    assert card is not None
    assert card.attack_bonus == 1
    assert card.evasion_bonus == 1


def test_find_tactic_returns_correct_fields() -> None:
    card = make_loader().find_tactic("target-lock")
    assert card is not None
    assert card.name == "Target Lock"
    assert "attack" in card.text.lower()


def test_find_hazard_returns_correct_fields() -> None:
    card = make_loader().find_hazard("flak-burst")
    assert card is not None
    assert card.name == "Flak Burst"
    assert card.trigger != ""
    assert card.text != ""


def test_find_aircraft_returns_none_for_unknown_id() -> None:
    assert make_loader().find_aircraft("does-not-exist") is None


def test_find_tactic_returns_none_for_unknown_id() -> None:
    assert make_loader().find_tactic("does-not-exist") is None


def test_find_hazard_returns_none_for_unknown_id() -> None:
    assert make_loader().find_hazard("does-not-exist") is None


def test_card_loader_is_used_when_creating_match_via_api(client) -> None:
    """Match created via POST /matches should be built from card definitions."""
    response = client.post("/matches")
    assert response.status_code == 201
    state = response.json()["match_state"]

    p1_aircraft = {a["aircraft_id"]: a for a in state["players"][0]["aircraft"]}
    assert p1_aircraft["aircraft-alpha"]["attack"] == 3
    assert p1_aircraft["aircraft-alpha"]["evasion"] == 4
    assert p1_aircraft["aircraft-alpha"]["max_fuel"] == 6
    assert p1_aircraft["aircraft-alpha"]["weapon"]["attack_bonus"] == 1
    assert p1_aircraft["aircraft-alpha"]["weapon"]["damage"] == 2
    assert p1_aircraft["aircraft-alpha"]["pilot"]["attack_bonus"] == 1
    assert p1_aircraft["aircraft-alpha"]["pilot"]["evasion_bonus"] == 0

    p2_aircraft = {a["aircraft_id"]: a for a in state["players"][1]["aircraft"]}
    assert p2_aircraft["aircraft-bravo"]["attack"] == 2
    assert p2_aircraft["aircraft-bravo"]["weapon"]["attack_bonus"] == 2
    assert p2_aircraft["aircraft-bravo"]["weapon"]["damage"] == 3
