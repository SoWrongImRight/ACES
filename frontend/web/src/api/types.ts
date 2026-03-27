// ─── Enums / Literals ───────────────────────────────────────────────────────

export type Phase = 'command' | 'ground' | 'air' | 'end'
export type Zone = 'runway' | 'air'
export type AttackTargetType = 'aircraft' | 'runway'

// ─── Sub-entities ────────────────────────────────────────────────────────────

export interface WeaponStateResponse {
  weapon_id: string
  name: string
  attack_bonus: number
  damage: number
  tags: string[]
  exhausted: boolean
}

export interface PilotStateResponse {
  pilot_id: string
  name: string
  attack_bonus: number
  evasion_bonus: number
  fuel_bonus: number
  structure_bonus: number
}

export interface RunwayStateResponse {
  health: number
  max_health: number
}

export interface AircraftStateResponse {
  aircraft_id: string
  owner_player_id: string
  name: string
  fuel: number
  max_fuel: number
  structure_rating: number
  max_structure_rating?: number
  attack: number
  evasion: number
  zone: Zone
  exhausted: boolean
  has_attacked_this_phase: boolean
  refit_this_turn: boolean
  destroyed: boolean
  weapon: WeaponStateResponse | null
  pilot: PilotStateResponse | null
}

export interface PlayerStateResponse {
  player_id: string
  display_name: string
  runway: RunwayStateResponse
  command_points: number
  hand_size: number
  aircraft: AircraftStateResponse[]
}

export interface ActiveBuffResponse {
  buff_id: string
  source: string
  target_id: string
  description: string
}

export interface ActiveHazardResponse {
  hazard_id: string
  name: string
  owner_player_id: string
  description?: string
}

export interface MatchEventResponse {
  sequence: number
  action_type: string
  actor_player_id: string
  outcome_type: string
  actor_entity_id: string | null
  target_type: AttackTargetType | null
  target_id: string | null
  sr_delta: number | null
  runway_damage: number | null
  roll: number | null
  destroyed_entity_id: string | null
  winner_player_id: string | null
}

// ─── Match State ─────────────────────────────────────────────────────────────

export interface MatchStateResponse {
  match_id: string
  turn_number: number
  active_player_id: string
  phase: Phase
  is_terminal: boolean
  winner_player_id: string | null
  loser_player_id: string | null
  event_history: MatchEventResponse[]
  active_buffs: ActiveBuffResponse[]
  active_hazards: ActiveHazardResponse[]
  players: PlayerStateResponse[]
}

// ─── API Response wrappers ───────────────────────────────────────────────────

export interface MatchListItem {
  match_id: string
  turn_number: number
  active_player_id: string
  phase: Phase
  is_terminal: boolean
}

export interface MatchListResponse {
  matches: MatchListItem[]
}

export interface CreateMatchResponse {
  match_id: string
  match_state: MatchStateResponse
}

export interface AdvancePhaseResponse {
  match_state: MatchStateResponse
}

export interface LegalTarget {
  target_type: AttackTargetType
  target_id: string
}

export interface ActionValidationResponse {
  status: string
  is_valid: boolean
  reason: string | null
  legal_actor_ids: string[]
  legal_target_ids: string[]
  legal_targets: LegalTarget[]
  match_state: MatchStateResponse
}

export interface ActionExecutionResponse {
  match_state: MatchStateResponse
  event?: MatchEventResponse
}

// ─── Action request bodies ───────────────────────────────────────────────────

export type ActionBody =
  | { action_type: 'launch_aircraft'; player_id: string; aircraft_id: string }
  | { action_type: 'refit_aircraft'; player_id: string; aircraft_id: string }
  | { action_type: 'return_to_runway'; player_id: string; aircraft_id: string }
  | {
      action_type: 'attack_aircraft'
      actor_player_id: string
      attacking_aircraft_id: string
      target: { target_type: AttackTargetType; target_id: string }
    }
  | {
      action_type: 'play_operation'
      player_id: string
      operation_name: string
      aircraft_id: string
    }
  | { action_type: 'play_hazard'; player_id: string; hazard_name: string }
