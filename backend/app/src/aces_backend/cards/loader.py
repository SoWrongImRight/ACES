from aces_backend.cards.definitions import (
    AircraftCardDefinition,
    PilotCardDefinition,
    WeaponCardDefinition,
)
from aces_backend.cards.source import CardSource


class CardLoader:
    """Aggregates card definitions across all available sets."""

    def __init__(self, source: CardSource) -> None:
        self._source = source

    def load_aircraft(self) -> list[AircraftCardDefinition]:
        return [
            AircraftCardDefinition.model_validate(card)
            for set_id in self._source.list_sets()
            for card in self._source.load_set(set_id).get("aircraft", [])
        ]

    def load_weapons(self) -> list[WeaponCardDefinition]:
        return [
            WeaponCardDefinition.model_validate(card)
            for set_id in self._source.list_sets()
            for card in self._source.load_set(set_id).get("weapons", [])
        ]

    def load_pilots(self) -> list[PilotCardDefinition]:
        return [
            PilotCardDefinition.model_validate(card)
            for set_id in self._source.list_sets()
            for card in self._source.load_set(set_id).get("pilots", [])
        ]

    def find_aircraft(self, card_id: str) -> AircraftCardDefinition | None:
        return next((c for c in self.load_aircraft() if c.card_id == card_id), None)

    def find_weapon(self, card_id: str) -> WeaponCardDefinition | None:
        return next((c for c in self.load_weapons() if c.card_id == card_id), None)

    def find_pilot(self, card_id: str) -> PilotCardDefinition | None:
        return next((c for c in self.load_pilots() if c.card_id == card_id), None)
