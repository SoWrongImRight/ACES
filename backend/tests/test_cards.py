from pathlib import Path

from aces_backend.cards.loader import CardLoader
from aces_backend.cards.source import LocalFileCardSource

# Resolve the cards directory relative to this test file.
# tests/ -> backend/ -> aces/ -> cards/
_CARDS_DIR = Path(__file__).resolve().parents[2] / "cards"


def make_loader() -> CardLoader:
    return CardLoader(LocalFileCardSource(_CARDS_DIR))


def test_base_set_is_discoverable() -> None:
    loader = make_loader()
    assert "base-set" in LocalFileCardSource(_CARDS_DIR).list_sets()


def test_loader_loads_all_aircraft_from_base_set() -> None:
    aircraft = make_loader().load_aircraft()
    ids = [a.card_id for a in aircraft]
    assert "falcon-one" in ids
    assert "eagle-three" in ids
    assert "viper-two" in ids
    assert "hawk-four" in ids


def test_loader_loads_all_weapons_from_base_set() -> None:
    weapons = make_loader().load_weapons()
    ids = [w.card_id for w in weapons]
    assert "20mm-cannon" in ids
    assert "sidewinder-missile" in ids


def test_loader_loads_all_pilots_from_base_set() -> None:
    pilots = make_loader().load_pilots()
    assert any(p.card_id == "maverick" for p in pilots)


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


def test_find_pilot_returns_correct_stats() -> None:
    card = make_loader().find_pilot("maverick")
    assert card is not None
    assert card.attack_bonus == 1


def test_find_aircraft_returns_none_for_unknown_id() -> None:
    assert make_loader().find_aircraft("does-not-exist") is None


def test_evasion_minimum_is_respected_across_all_aircraft() -> None:
    for card in make_loader().load_aircraft():
        assert card.evasion >= 4, f"{card.card_id} has evasion {card.evasion} (minimum is 4)"


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

    p2_aircraft = {a["aircraft_id"]: a for a in state["players"][1]["aircraft"]}
    assert p2_aircraft["aircraft-bravo"]["attack"] == 2
    assert p2_aircraft["aircraft-bravo"]["weapon"]["attack_bonus"] == 2
    assert p2_aircraft["aircraft-bravo"]["weapon"]["damage"] == 3
