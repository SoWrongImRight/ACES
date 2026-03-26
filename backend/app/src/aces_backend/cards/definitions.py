from pydantic import BaseModel, ConfigDict, Field


class AircraftCardDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="id")
    name: str
    attack: int
    evasion: int
    structure_rating: int
    max_fuel: int


class WeaponCardDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="id")
    name: str
    attack_bonus: int
    damage: int = 1


class PilotCardDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="id")
    name: str
    attack_bonus: int
