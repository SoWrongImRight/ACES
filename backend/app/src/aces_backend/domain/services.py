from dataclasses import dataclass, replace

from aces_backend.domain.models import (
    ActiveBuff,
    ActiveHazard,
    AircraftState,
    AttackTargetType,
    MatchEvent,
    MatchState,
    PlayerState,
    Zone,
)


MAX_EVENT_HISTORY = 50


@dataclass(slots=True)
class PhaseAdvanceValidationResult:
    is_valid: bool
    reason: str | None = None


class MatchFlow:
    """Deterministic match-flow helper for phase progression."""

    def __init__(self, cp_per_turn: int = 2) -> None:
        self._cp_per_turn = cp_per_turn

    def validate_phase_advance(
        self,
        match_state: MatchState,
        player_id: str,
    ) -> PhaseAdvanceValidationResult:
        if match_state.is_terminal:
            return PhaseAdvanceValidationResult(
                is_valid=False,
                reason="Phase advancement is not allowed after the match is over.",
            )

        if player_id != match_state.active_player_id:
            return PhaseAdvanceValidationResult(
                is_valid=False,
                reason="Only the active player may advance the phase.",
            )

        return PhaseAdvanceValidationResult(is_valid=True)

    def advance_phase(self, match_state: MatchState) -> MatchState:
        next_state = match_state.next_phase()
        if next_state.active_player_id == match_state.active_player_id:
            return next_state
        return self._clear_turn_flags(next_state)

    def _clear_turn_flags(self, match_state: MatchState) -> MatchState:
        updated_players = [
            replace(
                player,
                command_points=(
                    self._cp_per_turn
                    if player.player_id == match_state.active_player_id
                    else player.command_points
                ),
                aircraft=[
                    replace(
                        aircraft,
                        has_attacked_this_phase=False,
                        refit_this_turn=False,
                    )
                    for aircraft in player.aircraft
                ],
            )
            for player in match_state.players
        ]
        return replace(match_state, players=updated_players, active_buffs=[], active_hazards=[])


class MatchStateUpdater:
    """Applies deterministic state transitions after rules validation succeeds."""

    def restore_aircraft_fuel(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
        amount: int,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue
            updated_players.append(
                replace(
                    player,
                    aircraft=[
                        self._restore_fuel_if_matching(aircraft, aircraft_id, amount)
                        for aircraft in player.aircraft
                    ],
                )
            )
        return replace(match_state, players=updated_players)

    def decrement_cp(
        self,
        match_state: MatchState,
        player_id: str,
        amount: int,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue
            updated_players.append(replace(player, command_points=player.command_points - amount))
        return replace(match_state, players=updated_players)

    def add_active_buff(
        self,
        match_state: MatchState,
        buff: ActiveBuff,
    ) -> MatchState:
        return replace(match_state, active_buffs=[*match_state.active_buffs, buff])

    def consume_buffs_for_aircraft(
        self,
        match_state: MatchState,
        aircraft_id: str,
    ) -> MatchState:
        remaining = [b for b in match_state.active_buffs if b.aircraft_id != aircraft_id]
        return replace(match_state, active_buffs=remaining)

    def add_active_hazard(
        self,
        match_state: MatchState,
        hazard: ActiveHazard,
    ) -> MatchState:
        return replace(match_state, active_hazards=[*match_state.active_hazards, hazard])

    def consume_triggered_hazards(
        self,
        match_state: MatchState,
        triggered: list[ActiveHazard],
    ) -> MatchState:
        """Remove exactly the hazard objects that triggered, matched by identity."""
        triggered_ids = {id(h) for h in triggered}
        remaining = [h for h in match_state.active_hazards if id(h) not in triggered_ids]
        return replace(match_state, active_hazards=remaining)

    def launch_aircraft(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue

            updated_players.append(
                replace(
                    player,
                    aircraft=[
                        self._launch_if_matching(aircraft, aircraft_id)
                        for aircraft in player.aircraft
                    ],
                )
            )

        return replace(match_state, players=updated_players)

    def refit_aircraft(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue

            updated_players.append(
                replace(
                    player,
                    aircraft=[
                        self._refit_if_matching(aircraft, aircraft_id)
                        for aircraft in player.aircraft
                    ],
                )
            )

        return replace(match_state, players=updated_players)

    def return_to_runway(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue

            updated_players.append(
                replace(
                    player,
                    aircraft=[
                        self._return_if_matching(aircraft, aircraft_id)
                        for aircraft in player.aircraft
                    ],
                )
            )

        return replace(match_state, players=updated_players)

    def mark_aircraft_attacked(
        self,
        match_state: MatchState,
        player_id: str,
        aircraft_id: str,
    ) -> MatchState:
        updated_players: list[PlayerState] = []
        for player in match_state.players:
            if player.player_id != player_id:
                updated_players.append(player)
                continue

            updated_players.append(
                replace(
                    player,
                    aircraft=[
                        self._mark_attacked_if_matching(aircraft, aircraft_id)
                        for aircraft in player.aircraft
                    ],
                )
            )

        return replace(match_state, players=updated_players)

    def resolve_attack(
        self,
        match_state: MatchState,
        player_id: str,
        attacking_aircraft_id: str,
        target_id: str,
        target_type: AttackTargetType,
        structure_rating_delta: int = 0,
        runway_damage: int = 0,
    ) -> MatchState:
        updated_match_state = self.mark_aircraft_attacked(
            match_state=match_state,
            player_id=player_id,
            aircraft_id=attacking_aircraft_id,
        )
        if structure_rating_delta == 0 and runway_damage == 0:
            return updated_match_state

        updated_players: list[PlayerState] = []
        for player in updated_match_state.players:
            updated_players.append(
                replace(
                    player,
                    runway=self._apply_runway_damage_if_matching(
                        player=player,
                        target_id=target_id,
                        target_type=target_type,
                        runway_damage=runway_damage,
                    ),
                    aircraft=[
                        self._apply_aircraft_damage_if_matching(
                            aircraft,
                            target_id=target_id,
                            target_type=target_type,
                            structure_rating_delta=structure_rating_delta,
                        )
                        for aircraft in player.aircraft
                    ],
                )
            )

        return replace(updated_match_state, players=updated_players)

    def _restore_fuel_if_matching(
        self,
        aircraft: AircraftState,
        aircraft_id: str,
        amount: int,
    ) -> AircraftState:
        if aircraft.aircraft_id != aircraft_id:
            return aircraft
        return replace(aircraft, fuel=min(aircraft.fuel + amount, aircraft.max_fuel))

    def _launch_if_matching(
        self,
        aircraft: AircraftState,
        aircraft_id: str,
    ) -> AircraftState:
        if aircraft.aircraft_id != aircraft_id:
            return aircraft
        return replace(aircraft, zone=Zone.AIR)

    def _refit_if_matching(
        self,
        aircraft: AircraftState,
        aircraft_id: str,
    ) -> AircraftState:
        if aircraft.aircraft_id != aircraft_id:
            return aircraft
        return replace(
            aircraft,
            fuel=aircraft.max_fuel,
            weapon=(
                replace(aircraft.weapon, exhausted=False)
                if aircraft.weapon is not None
                else None
            ),
            exhausted=False,
            refit_this_turn=True,
        )

    def _return_if_matching(
        self,
        aircraft: AircraftState,
        aircraft_id: str,
    ) -> AircraftState:
        if aircraft.aircraft_id != aircraft_id:
            return aircraft
        return replace(aircraft, zone=Zone.RUNWAY)

    def _mark_attacked_if_matching(
        self,
        aircraft: AircraftState,
        aircraft_id: str,
    ) -> AircraftState:
        if aircraft.aircraft_id != aircraft_id:
            return aircraft
        return replace(
            aircraft,
            fuel=max(aircraft.fuel - 1, 0),
            weapon=(
                replace(aircraft.weapon, exhausted=True)
                if aircraft.weapon is not None and not aircraft.weapon.exhausted
                else aircraft.weapon
            ),
            has_attacked_this_phase=True,
            exhausted=True,
        )

    def _apply_aircraft_damage_if_matching(
        self,
        aircraft: AircraftState,
        target_id: str,
        target_type: AttackTargetType,
        structure_rating_delta: int,
    ) -> AircraftState:
        if (
            target_type != AttackTargetType.AIRCRAFT
            or aircraft.aircraft_id != target_id
            or structure_rating_delta == 0
        ):
            return aircraft

        next_structure_rating = aircraft.structure_rating + structure_rating_delta
        return replace(
            aircraft,
            structure_rating=max(next_structure_rating, 0),
            destroyed=next_structure_rating <= 0,
        )

    def _apply_runway_damage_if_matching(
        self,
        player: PlayerState,
        target_id: str,
        target_type: AttackTargetType,
        runway_damage: int,
    ):
        if (
            target_type != AttackTargetType.RUNWAY
            or player.player_id != target_id
            or runway_damage == 0
        ):
            return player.runway

        next_health = player.runway.health - runway_damage
        return replace(
            player.runway,
            health=max(next_health, 0),
        )


class MatchOutcomeEvaluator:
    """Evaluates terminal match outcomes from the canonical backend state."""

    def apply_outcome(self, match_state: MatchState) -> MatchState:
        if match_state.is_terminal:
            return match_state

        for player in match_state.players:
            if player.runway.health <= 0:
                winner = next(
                    (
                        candidate.player_id
                        for candidate in match_state.players
                        if candidate.player_id != player.player_id
                    ),
                    None,
                )
                return replace(
                    match_state,
                    is_terminal=True,
                    winner_player_id=winner,
                    loser_player_id=player.player_id,
                )

            if any(not aircraft.destroyed for aircraft in player.aircraft):
                continue

            winner = next(
                (
                    candidate.player_id
                    for candidate in match_state.players
                    if candidate.player_id != player.player_id
                ),
                None,
            )
            return replace(
                match_state,
                is_terminal=True,
                winner_player_id=winner,
                loser_player_id=player.player_id,
            )

        return match_state


class MatchHistoryManager:
    """Maintains a small deterministic event history on the canonical match state."""

    def append_events(
        self,
        match_state: MatchState,
        events: list[MatchEvent],
    ) -> tuple[MatchState, list[MatchEvent]]:
        if not events:
            return match_state, []

        sequence = match_state.next_event_sequence
        sequenced_events = [
            replace(event, sequence=sequence + index)
            for index, event in enumerate(events)
        ]
        next_history = (match_state.event_history + sequenced_events)[-MAX_EVENT_HISTORY:]
        return (
            replace(
                match_state,
                event_history=next_history,
                next_event_sequence=sequence + len(sequenced_events),
            ),
            sequenced_events,
        )
