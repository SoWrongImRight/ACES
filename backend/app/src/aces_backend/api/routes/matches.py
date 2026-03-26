from fastapi import APIRouter, Depends, HTTPException, status

from aces_backend.api.dependencies import get_card_loader, get_match_repository, get_rules_engine, get_settings
from aces_backend.cards.loader import CardLoader
from aces_backend.config import GameSettings
from aces_backend.api.schemas import (
    ActionExecutionRequest,
    ActiveBuffResponse,
    AircraftStateResponse,
    ActionExecutionResponse,
    ActionIntentRequest,
    ActionResultResponse,
    ActionValidationResponse,
    AdvancePhaseRequest,
    AdvancePhaseResponse,
    CreateMatchResponse,
    MatchListResponse,
    MatchEventResponse,
    MatchStateResponse,
    MatchSummaryResponse,
    PilotStateResponse,
    PlayerStateResponse,
    PlayOperationActionRequest,
    RunwayStateResponse,
    TargetReferenceRequest,
    WeaponStateResponse,
)
from aces_backend.domain.models import AircraftState, MatchState, PlayerState
from aces_backend.domain.repository import MatchRepository
from aces_backend.domain.services import MatchFlow
from aces_backend.rules.engine import ActionIntent, RulesEngine, TargetReference

router = APIRouter(prefix="/matches", tags=["matches"])


def to_aircraft_response(aircraft_state: AircraftState) -> AircraftStateResponse:
    return AircraftStateResponse(
        aircraft_id=aircraft_state.aircraft_id,
        owner_player_id=aircraft_state.owner_player_id,
        name=aircraft_state.name,
        fuel=aircraft_state.fuel,
        max_fuel=aircraft_state.max_fuel,
        structure_rating=aircraft_state.structure_rating,
        attack=aircraft_state.attack,
        evasion=aircraft_state.evasion,
        zone=aircraft_state.zone,
        exhausted=aircraft_state.exhausted,
        has_attacked_this_phase=aircraft_state.has_attacked_this_phase,
        refit_this_turn=aircraft_state.refit_this_turn,
        destroyed=aircraft_state.destroyed,
        weapon=(
            WeaponStateResponse(
                weapon_id=aircraft_state.weapon.weapon_id,
                name=aircraft_state.weapon.name,
                attack_bonus=aircraft_state.weapon.attack_bonus,
                damage=aircraft_state.weapon.damage,
                tags=aircraft_state.weapon.tags,
                exhausted=aircraft_state.weapon.exhausted,
            )
            if aircraft_state.weapon is not None
            else None
        ),
        pilot=(
            PilotStateResponse(
                pilot_id=aircraft_state.pilot.pilot_id,
                name=aircraft_state.pilot.name,
                attack_bonus=aircraft_state.pilot.attack_bonus,
                evasion_bonus=aircraft_state.pilot.evasion_bonus,
                fuel_bonus=aircraft_state.pilot.fuel_bonus,
                structure_bonus=aircraft_state.pilot.structure_bonus,
            )
            if aircraft_state.pilot is not None
            else None
        ),
    )


def to_player_response(player_state: PlayerState) -> PlayerStateResponse:
    return PlayerStateResponse(
        player_id=player_state.player_id,
        display_name=player_state.display_name,
        runway=RunwayStateResponse(
            health=player_state.runway.health,
            max_health=player_state.runway.max_health,
        ),
        command_points=player_state.command_points,
        hand_size=player_state.hand_size,
        aircraft=[to_aircraft_response(aircraft) for aircraft in player_state.aircraft],
    )


def to_match_event_response(event) -> MatchEventResponse:
    return MatchEventResponse(
        sequence=event.sequence,
        action_type=event.action_type,
        actor_player_id=event.actor_player_id,
        outcome_type=event.outcome_type,
        actor_entity_id=event.actor_entity_id,
        target_type=event.target_type,
        target_id=event.target_id,
        from_zone=event.from_zone,
        to_zone=event.to_zone,
        sr_delta=event.sr_delta,
        runway_damage=event.runway_damage,
        roll=event.roll,
        destroyed_entity_id=event.destroyed_entity_id,
        winner_player_id=event.winner_player_id,
    )


def to_match_response(match_state: MatchState) -> MatchStateResponse:
    return MatchStateResponse(
        match_id=match_state.match_id,
        turn_number=match_state.turn_number,
        active_player_id=match_state.active_player_id,
        phase=match_state.phase,
        is_terminal=match_state.is_terminal,
        winner_player_id=match_state.winner_player_id,
        loser_player_id=match_state.loser_player_id,
        event_history=[to_match_event_response(event) for event in match_state.event_history],
        active_buffs=[
            ActiveBuffResponse(
                tactic_id=buff.tactic_id,
                aircraft_id=buff.aircraft_id,
                player_id=buff.player_id,
                attack_delta=buff.attack_delta,
                evasion_delta=buff.evasion_delta,
                self_damage=buff.self_damage,
            )
            for buff in match_state.active_buffs
        ],
        players=[to_player_response(player) for player in match_state.players],
    )


def to_match_summary(match_state: MatchState) -> MatchSummaryResponse:
    return MatchSummaryResponse(
        match_id=match_state.match_id,
        turn_number=match_state.turn_number,
        active_player_id=match_state.active_player_id,
        phase=match_state.phase,
    )


def get_existing_match(
    match_id: str,
    match_repository: MatchRepository,
) -> MatchState:
    match_state = match_repository.get_match(match_id)
    if match_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match '{match_id}' was not found.",
        )
    return match_state


@router.get("", response_model=MatchListResponse)
def list_matches(
    match_repository: MatchRepository = Depends(get_match_repository),
) -> MatchListResponse:
    return MatchListResponse(
        matches=[to_match_summary(match_state) for match_state in match_repository.list_matches()]
    )


@router.post(
    "",
    response_model=CreateMatchResponse,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
)
def create_match(
    match_repository: MatchRepository = Depends(get_match_repository),
    settings: GameSettings = Depends(get_settings),
    card_loader: CardLoader = Depends(get_card_loader),
) -> CreateMatchResponse:
    match_state = match_repository.create_match(
        cp_per_turn=settings.cp_per_turn,
        runway_health=settings.runway_health,
        card_loader=card_loader,
    )
    return CreateMatchResponse(
        match_id=match_state.match_id,
        match_state=to_match_response(match_state),
    )


@router.get("/{match_id}", response_model=MatchStateResponse, response_model_exclude_none=True)
def get_match(
    match_id: str,
    match_repository: MatchRepository = Depends(get_match_repository),
) -> MatchStateResponse:
    return to_match_response(get_existing_match(match_id, match_repository))


@router.post(
    "/{match_id}/advance-phase",
    response_model=AdvancePhaseResponse,
    response_model_exclude_none=True,
)
def advance_phase(
    match_id: str,
    request: AdvancePhaseRequest,
    match_repository: MatchRepository = Depends(get_match_repository),
    settings: GameSettings = Depends(get_settings),
) -> AdvancePhaseResponse:
    match_state = get_existing_match(match_id, match_repository)
    match_flow = MatchFlow(cp_per_turn=settings.cp_per_turn)
    validation = match_flow.validate_phase_advance(match_state, request.player_id)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=validation.reason,
        )

    updated_match_state = match_flow.advance_phase(match_state)
    match_repository.save_match(updated_match_state)
    return AdvancePhaseResponse(status="advanced", match_state=to_match_response(updated_match_state))


@router.post(
    "/{match_id}/actions/preview",
    response_model=ActionValidationResponse,
    response_model_exclude_none=True,
)
def preview_action(
    match_id: str,
    request: ActionIntentRequest,
    match_repository: MatchRepository = Depends(get_match_repository),
    rules_engine: RulesEngine = Depends(get_rules_engine),
) -> ActionValidationResponse:
    match_state = get_existing_match(match_id, match_repository)
    result = rules_engine.preview_action(
        match_state,
        ActionIntent(
            action_type=request.action_type,
            actor_id=request.actor_id,
            player_id=request.player_id,
            selected_target_ids=request.selected_target_ids,
            selected_targets=[
                TargetReference(
                    target_type=target.target_type,
                    target_id=target.target_id,
                )
                for target in request.selected_targets
            ],
            operation_name=request.operation_name,
        ),
    )
    return ActionValidationResponse(
        status="validated" if result.is_valid else "rejected",
        is_valid=result.is_valid,
        reason=result.reason,
        legal_actor_ids=result.legal_actor_ids,
        legal_target_ids=result.legal_target_ids,
        legal_targets=[
            TargetReferenceRequest(
                target_type=target.target_type,
                target_id=target.target_id,
            )
            for target in result.legal_targets
        ],
        match_state=to_match_response(match_state),
    )


@router.post(
    "/{match_id}/actions",
    response_model=ActionExecutionResponse,
    response_model_exclude_none=True,
)
def execute_action(
    match_id: str,
    request: ActionExecutionRequest,
    match_repository: MatchRepository = Depends(get_match_repository),
    rules_engine: RulesEngine = Depends(get_rules_engine),
) -> ActionExecutionResponse:
    match_state = get_existing_match(match_id, match_repository)
    if request.action_type == "attack_aircraft":
        action_intent = ActionIntent(
            action_type=request.action_type,
            actor_id=request.attacking_aircraft_id,
            player_id=request.actor_player_id,
            selected_targets=[
                TargetReference(
                    target_type=request.target.target_type,
                    target_id=request.target.target_id,
                )
            ],
        )
    elif isinstance(request, PlayOperationActionRequest):
        action_intent = ActionIntent(
            action_type=request.action_type,
            actor_id=request.aircraft_id,
            player_id=request.player_id,
            operation_name=request.operation_name,
        )
    else:
        action_intent = ActionIntent(
            action_type=request.action_type,
            actor_id=request.aircraft_id,
            player_id=request.player_id,
        )
    result = rules_engine.execute_action(
        match_state,
        action_intent,
    )
    if result.is_valid:
        match_repository.save_match(result.match_state)

    return ActionExecutionResponse(
        status="resolved" if result.is_valid else "rejected",
        action_type=request.action_type,
        reason=result.reason,
        match_state=to_match_response(result.match_state),
        action_result=(
            ActionResultResponse(
                aircraft_id=result.resolution.aircraft_id,
                action_type=(
                    result.resolution.action_type
                    if request.action_type == "attack_aircraft"
                    else None
                ),
                attacking_aircraft_id=(
                    result.resolution.aircraft_id
                    if request.action_type == "attack_aircraft"
                    else None
                ),
                previous_zone=result.resolution.previous_zone,
                current_zone=result.resolution.current_zone,
                target_type=result.resolution.target_type,
                target_id=result.resolution.target_id,
                executed=result.resolution.executed,
                result_type=result.resolution.result_type,
                structure_rating_change=result.resolution.structure_rating_change,
                target_structure_rating=result.resolution.target_structure_rating,
                runway_health_change=result.resolution.runway_health_change,
                target_runway_health=result.resolution.target_runway_health,
                target_destroyed=result.resolution.target_destroyed,
                fuel=result.resolution.fuel,
                max_fuel=result.resolution.max_fuel,
                exhausted=result.resolution.exhausted,
                refit_this_turn=result.resolution.refit_this_turn,
            )
            if result.resolution is not None
            else None
        ),
        emitted_events=[to_match_event_response(event) for event in result.events],
    )
