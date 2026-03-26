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
    attack_bonus: int = 0
    evasion_bonus: int = 0
    fuel_bonus: int = 0
    structure_bonus: int = 0


class TacticCardDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="id")
    name: str
    text: str


class HazardCardDefinition(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="id")
    name: str
    trigger: str
    text: str
