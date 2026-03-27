import type { Phase, PlayerStateResponse } from '../../api/types'

interface Props {
  turnNumber: number
  phase: Phase
  activePlayerId: string
  players: PlayerStateResponse[]
  myPlayerId: string | null
  isTerminal: boolean
  winnerPlayerId: string | null
}

const PHASE_LABELS: Record<Phase, string> = {
  command: 'COMMAND',
  ground: 'GROUND',
  air: 'AIR',
  end: 'END',
}

const PHASE_COLORS: Record<Phase, string> = {
  command: 'text-accent-blue border-accent-blue',
  ground: 'text-accent-amber border-accent-amber',
  air: 'text-accent-green border-accent-green',
  end: 'text-accent-muted border-accent-muted',
}

export function PhaseBar({
  turnNumber,
  phase,
  activePlayerId,
  players,
  myPlayerId,
  isTerminal,
  winnerPlayerId,
}: Props) {
  const activePlayer = players.find((p) => p.player_id === activePlayerId)
  const myPlayer = players.find((p) => p.player_id === myPlayerId)
  const isMyTurn = myPlayerId === activePlayerId
  const winnerName = players.find((p) => p.player_id === winnerPlayerId)?.display_name

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-surface-elevated border-b border-surface-border">
      {/* Left: Turn + Phase */}
      <div className="flex items-center gap-4">
        <div className="font-mono text-xs text-accent-muted">
          TURN <span className="text-white font-bold">{turnNumber}</span>
        </div>
        <div
          className={`font-mono text-xs font-bold border px-2 py-0.5 rounded ${PHASE_COLORS[phase]}`}
        >
          {PHASE_LABELS[phase]} PHASE
        </div>
      </div>

      {/* Center: Active player + terminal state */}
      <div className="font-mono text-xs text-center">
        {isTerminal ? (
          <span className="text-accent-amber font-bold">
            MATCH OVER {winnerName ? `— ${winnerName} wins` : ''}
          </span>
        ) : (
          <span>
            <span className="text-accent-muted">Active: </span>
            <span className={isMyTurn ? 'text-accent-green font-bold' : 'text-accent-red font-bold'}>
              {activePlayer?.display_name ?? activePlayerId}
              {isMyTurn ? ' (you)' : ''}
            </span>
          </span>
        )}
      </div>

      {/* Right: CP */}
      <div className="font-mono text-xs">
        {myPlayer && (
          <span>
            <span className="text-accent-muted">CP </span>
            <span className="text-accent-amber font-bold">{myPlayer.command_points}</span>
          </span>
        )}
      </div>
    </div>
  )
}
