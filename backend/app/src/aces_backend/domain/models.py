from dataclasses import dataclass, field
from enum import StrEnum


class Phase(StrEnum):
    COMMAND = "command"
    GROUND = "ground"
    AIR = "air"
    END = "end"


class Zone(StrEnum):
    RUNWAY = "runway"
    AIR = "air"


class AttackTargetType(StrEnum):
    AIRCRAFT = "aircraft"
    RUNWAY = "runway"


PHASE_ORDER: tuple[Phase, ...] = (
    Phase.COMMAND,
    Phase.GROUND,
    Phase.AIR,
    Phase.END,
)


@dataclass(slots=True)
class RunwayState:
    health: int = 20
    max_health: int = 20


@dataclass(slots=True)
class WeaponState:
    weapon_id: str
    name: str
    attack_bonus: int
    damage: int = 1
    exhausted: bool = False


@dataclass(slots=True)
class PilotState:
    pilot_id: str
    name: str
    attack_bonus: int = 0


@dataclass(slots=True)
class MatchEvent:
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
    roll: int | None = None
    destroyed_entity_id: str | None = None
    winner_player_id: str | None = None


@dataclass(slots=True)
class AircraftState:
    aircraft_id: str
    owner_player_id: str
    name: str
    fuel: int
    max_fuel: int
    structure_rating: int
    attack: int
    evasion: int
    zone: Zone
    weapon: WeaponState | None = None
    pilot: PilotState | None = None
    exhausted: bool = False
    has_attacked_this_phase: bool = False
    refit_this_turn: bool = False
    destroyed: bool = False


@dataclass(slots=True)
class PlayerState:
    player_id: str
    display_name: str
    runway: RunwayState = field(default_factory=RunwayState)
    command_points: int = 0
    hand_size: int = 5
    aircraft: list[AircraftState] = field(default_factory=list)

    def aircraft_in_zone(self, zone: Zone) -> list[AircraftState]:
        return [aircraft for aircraft in self.aircraft if aircraft.zone == zone]


@dataclass(slots=True)
class MatchState:
    match_id: str
    turn_number: int
    active_player_id: str
    phase: Phase
    players: list[PlayerState]
    is_terminal: bool = False
    winner_player_id: str | None = None
    loser_player_id: str | None = None
    event_history: list[MatchEvent] = field(default_factory=list)
    next_event_sequence: int = 1

    def get_player(self, player_id: str) -> PlayerState | None:
        return next((player for player in self.players if player.player_id == player_id), None)

    def get_aircraft(self, aircraft_id: str) -> AircraftState | None:
        return next(
            (
                aircraft
                for player in self.players
                for aircraft in player.aircraft
                if aircraft.aircraft_id == aircraft_id
            ),
            None,
        )

    def next_phase(self) -> "MatchState":
        phase_index = PHASE_ORDER.index(self.phase)
        if phase_index < len(PHASE_ORDER) - 1:
            return MatchState(
                match_id=self.match_id,
                turn_number=self.turn_number,
                active_player_id=self.active_player_id,
                phase=PHASE_ORDER[phase_index + 1],
                players=self.players,
                is_terminal=self.is_terminal,
                winner_player_id=self.winner_player_id,
                loser_player_id=self.loser_player_id,
                event_history=self.event_history,
                next_event_sequence=self.next_event_sequence,
            )

        player_ids = [player.player_id for player in self.players]
        active_index = player_ids.index(self.active_player_id)
        next_index = (active_index + 1) % len(player_ids)
        next_turn_number = self.turn_number + (1 if next_index == 0 else 0)
        return MatchState(
            match_id=self.match_id,
            turn_number=next_turn_number,
            active_player_id=player_ids[next_index],
            phase=Phase.COMMAND,
            players=self.players,
            is_terminal=self.is_terminal,
            winner_player_id=self.winner_player_id,
            loser_player_id=self.loser_player_id,
            event_history=self.event_history,
            next_event_sequence=self.next_event_sequence,
        )
