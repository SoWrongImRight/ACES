import type {
  ActionBody,
  ActionExecutionResponse,
  ActionValidationResponse,
  AdvancePhaseResponse,
  AttackTargetType,
  CreateMatchResponse,
  MatchListResponse,
  MatchStateResponse,
} from './types'

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function createMatch(): Promise<CreateMatchResponse> {
  return request<CreateMatchResponse>('/matches', { method: 'POST' })
}

export async function listMatches(): Promise<MatchListResponse> {
  return request<MatchListResponse>('/matches')
}

export async function getMatch(matchId: string): Promise<MatchStateResponse> {
  return request<MatchStateResponse>(`/matches/${matchId}`)
}

export async function executeAction(
  matchId: string,
  body: ActionBody,
): Promise<ActionExecutionResponse> {
  return request<ActionExecutionResponse>(`/matches/${matchId}/actions`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function advancePhase(
  matchId: string,
  playerId: string,
): Promise<AdvancePhaseResponse> {
  return request<AdvancePhaseResponse>(`/matches/${matchId}/advance-phase`, {
    method: 'POST',
    body: JSON.stringify({ player_id: playerId }),
  })
}

export async function previewAttack(
  matchId: string,
  actorPlayerId: string,
  attackingAircraftId: string,
  targetType?: AttackTargetType,
  targetId?: string,
): Promise<ActionValidationResponse> {
  const body: Record<string, unknown> = {
    action_type: 'attack_aircraft',
    actor_player_id: actorPlayerId,
    attacking_aircraft_id: attackingAircraftId,
  }
  if (targetType && targetId) {
    body.target = { target_type: targetType, target_id: targetId }
  }
  return request<ActionValidationResponse>(`/matches/${matchId}/preview-action`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
