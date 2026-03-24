from typing import Annotated, Literal

from pydantic import BaseModel, Field, Discriminator

from aces_backend.domain.models import AttackTargetType, Phase, Zone


class HealthResponse(BaseModel):
    status: str = "ok"


class RunwayStateResponse(BaseModel):
    health: int
    max_health: int


class AircraftStateResponse(BaseModel):
    aircraft_id: str
    owner_player_id: str
    name: str
    fuel: int
    max_fuel: int
    structure_rating: int
    attack: int
    evasion: int
    zone: Zone
    exhausted: bool
    has_attacked_this_phase: bool
    refit_this_turn: bool
    destroyed: bool
    weapon: "WeaponStateResponse | None" = None
    pilot: "PilotStateResponse | None" = None


class WeaponStateResponse(BaseModel):
    weapon_id: str
    name: str
    attack_bonus: int
    exhausted: bool


class PilotStateResponse(BaseModel):
    pilot_id: str
    name: str
    attack_bonus: int


class PlayerStateResponse(BaseModel):
    player_id: str
    display_name: str
    runway: RunwayStateResponse
    command_points: int
    hand_size: int
    aircraft: list[AircraftStateResponse]


class MatchEventResponse(BaseModel):
    sequence: int
    action_type: str
    actor_player_id: str
    outcome_type: str
    actor_entity_id: str | None = None
    target_type: AttackTargetType | None = None
    target_id: str | None = None
    from_zone: Zone | None = None
    to_zone: Zone | None = None
    sr_delta: int | None = None
    runway_damage: int | None = None
    destroyed_entity_id: str | None = None
    winner_player_id: str | None = None


class MatchStateResponse(BaseModel):
    match_id: str
    turn_number: int
    active_player_id: str
    phase: Phase
    is_terminal: bool
    winner_player_id: str | None = None
    loser_player_id: str | None = None
    event_history: list[MatchEventResponse]
    players: list[PlayerStateResponse]


class MatchSummaryResponse(BaseModel):
    match_id: str
    turn_number: int
    active_player_id: str
    phase: Phase


class MatchListResponse(BaseModel):
    matches: list[MatchSummaryResponse]


class CreateMatchResponse(BaseModel):
    match_id: str
    match_state: MatchStateResponse


class TargetReferenceRequest(BaseModel):
    target_type: AttackTargetType
    target_id: str


class ActionIntentRequest(BaseModel):
    action_type: str = Field(..., description="Client-declared action intent.")
    actor_id: str = Field(..., description="Card or entity attempting the action.")
    player_id: str = Field(..., description="Player submitting the action.")
    selected_target_ids: list[str] = Field(
        default_factory=list,
        description="Optional client-selected targets for validation.",
    )
    selected_targets: list[TargetReferenceRequest] = Field(
        default_factory=list,
        description="Optional typed targets for validation.",
    )


class ActionValidationResponse(BaseModel):
    status: str
    is_valid: bool
    reason: str | None = None
    legal_actor_ids: list[str]
    legal_target_ids: list[str]
    legal_targets: list[TargetReferenceRequest]
    match_state: MatchStateResponse


class AdvancePhaseRequest(BaseModel):
    player_id: str = Field(..., description="Player requesting phase advancement.")


class AdvancePhaseResponse(BaseModel):
    status: str
    match_state: MatchStateResponse


class LaunchAircraftActionRequest(BaseModel):
    action_type: Literal["launch_aircraft"]
    player_id: str = Field(..., description="Player performing the action.")
    aircraft_id: str = Field(..., description="Aircraft attempting to launch.")


class RefitAircraftActionRequest(BaseModel):
    action_type: Literal["refit_aircraft"]
    player_id: str = Field(..., description="Player performing the action.")
    aircraft_id: str = Field(..., description="Aircraft attempting to refit.")


class ReturnToRunwayActionRequest(BaseModel):
    action_type: Literal["return_to_runway"]
    player_id: str = Field(..., description="Player performing the action.")
    aircraft_id: str = Field(..., description="Aircraft attempting to return to runway.")


class AttackAircraftActionRequest(BaseModel):
    action_type: Literal["attack_aircraft"]
    actor_player_id: str = Field(..., description="Player performing the attack.")
    attacking_aircraft_id: str = Field(..., description="Aircraft performing the attack.")
    target: TargetReferenceRequest = Field(..., description="Typed target for this attack.")


ActionExecutionRequest = Annotated[
    LaunchAircraftActionRequest
    | RefitAircraftActionRequest
    | ReturnToRunwayActionRequest
    | AttackAircraftActionRequest,
    Discriminator("action_type"),
]


class ActionResultResponse(BaseModel):
    aircraft_id: str
    action_type: str | None = None
    attacking_aircraft_id: str | None = None
    previous_zone: Zone
    current_zone: Zone
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


class ActionExecutionResponse(BaseModel):
    status: str
    action_type: str
    reason: str | None = None
    match_state: MatchStateResponse
    action_result: ActionResultResponse | None = None
    emitted_events: list[MatchEventResponse] = Field(default_factory=list)
