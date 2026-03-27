import { useState } from 'react'
import type { MatchEventResponse } from '../../api/types'

interface Props {
  events: MatchEventResponse[]
  players: Array<{ player_id: string; display_name: string }>
}

function describeEvent(e: MatchEventResponse, playerName: (id: string) => string): string {
  const actor = playerName(e.actor_player_id)
  switch (e.action_type) {
    case 'launch_aircraft':
      return `${actor} launched ${e.actor_entity_id ?? 'aircraft'}`
    case 'refit_aircraft':
      return `${actor} refitted ${e.actor_entity_id ?? 'aircraft'}`
    case 'return_to_runway':
      return `${actor} returned ${e.actor_entity_id ?? 'aircraft'} to runway`
    case 'attack_aircraft': {
      const roll = e.roll != null ? ` (roll: ${e.roll})` : ''
      const dmg = e.sr_delta != null ? ` −${Math.abs(e.sr_delta)} SR` : ''
      const rwDmg = e.runway_damage != null ? ` −${e.runway_damage} RWY` : ''
      const destroyed = e.destroyed_entity_id ? ` [DESTROYED]` : ''
      return `${actor} attacked ${e.target_id ?? 'target'}${roll}${dmg}${rwDmg}${destroyed} — ${e.outcome_type}`
    }
    case 'play_operation':
      return `${actor} played operation`
    case 'play_hazard':
      return `${actor} played hazard`
    case 'advance_phase':
      return `${actor} advanced phase → ${e.outcome_type}`
    default:
      return `${actor}: ${e.action_type} (${e.outcome_type})`
  }
}

function outcomeColor(outcome: string): string {
  if (outcome === 'hit') return 'text-accent-red'
  if (outcome === 'miss') return 'text-accent-muted'
  if (outcome === 'destroyed') return 'text-accent-amber'
  if (outcome === 'success') return 'text-accent-green'
  return 'text-accent-muted'
}

export function EventLog({ events, players }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  function playerName(id: string): string {
    return players.find((p) => p.player_id === id)?.display_name ?? id.slice(0, 8)
  }

  const recent = [...events].sort((a, b) => b.sequence - a.sequence).slice(0, 20)

  return (
    <div className="border-t border-surface-border bg-surface">
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center justify-between px-4 py-2 hover:bg-surface-elevated transition-colors"
      >
        <span className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
          Event Log ({events.length})
        </span>
        <span className="text-accent-muted text-xs font-mono">{collapsed ? '▲' : '▼'}</span>
      </button>

      {!collapsed && (
        <div className="max-h-40 overflow-y-auto px-4 pb-3">
          {recent.length === 0 ? (
            <div className="text-xs font-mono text-accent-muted italic">No events yet.</div>
          ) : (
            <div className="flex flex-col gap-0.5">
              {recent.map((e) => (
                <div key={e.sequence} className="flex items-baseline gap-2 text-[10px] font-mono">
                  <span className="text-surface-border shrink-0">#{e.sequence}</span>
                  <span className={`shrink-0 ${outcomeColor(e.outcome_type)}`}>
                    [{e.outcome_type}]
                  </span>
                  <span className="text-accent-muted">{describeEvent(e, playerName)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
