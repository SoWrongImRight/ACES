import { useCallback, useState } from 'react'
import type { ActionBody, AttackTargetType, LegalTarget, MatchStateResponse } from '../../api/types'
import { EventLog } from '../log/EventLog'
import { ActionPanel } from '../phase/ActionPanel'
import { PhaseBar } from '../phase/PhaseBar'
import { PlayerZone } from './PlayerZone'

interface Props {
  match: MatchStateResponse
  myPlayerId: string
  error: string | null
  onAction: (body: ActionBody) => Promise<void>
  onAdvancePhase: () => Promise<void>
  onPreviewAttack: (aircraftId: string) => Promise<{ legal_targets: LegalTarget[] } | null>
  onBack: () => void
}

export function MatchBoard({
  match,
  myPlayerId,
  error,
  onAction,
  onAdvancePhase,
  onPreviewAttack,
  onBack,
}: Props) {
  const [selectedAircraftId, setSelectedAircraftId] = useState<string | null>(null)
  const [isTargeting, setIsTargeting] = useState(false)
  const [legalTargets, setLegalTargets] = useState<LegalTarget[]>([])

  const myPlayer = match.players.find((p) => p.player_id === myPlayerId)
  const opponentPlayer = match.players.find((p) => p.player_id !== myPlayerId)

  const legalTargetIds = legalTargets
    .filter((t) => t.target_type === 'aircraft')
    .map((t) => t.target_id)

  const legalRunwayTargetIds = legalTargets
    .filter((t) => t.target_type === 'runway')
    .map((t) => t.target_id)

  const cancelTargeting = useCallback(() => {
    setIsTargeting(false)
    setSelectedAircraftId(null)
    setLegalTargets([])
  }, [])

  const handleSelectAircraftOnBoard = useCallback(
    async (aircraftId: string, ownerPlayerId: string) => {
      // If we're targeting, clicking a legal target fires the attack
      if (isTargeting && selectedAircraftId) {
        const isLegal = legalTargetIds.includes(aircraftId)
        if (isLegal) {
          await onAction({
            action_type: 'attack_aircraft',
            actor_player_id: myPlayerId,
            attacking_aircraft_id: selectedAircraftId,
            target: { target_type: 'aircraft', target_id: aircraftId },
          })
          cancelTargeting()
        }
        return
      }

      // Otherwise select attacker (must be mine, in air, not attacked)
      if (ownerPlayerId !== myPlayerId) return
      setSelectedAircraftId((prev) => (prev === aircraftId ? null : aircraftId))
      setIsTargeting(false)
      setLegalTargets([])
    },
    [isTargeting, selectedAircraftId, legalTargetIds, myPlayerId, onAction, cancelTargeting],
  )

  const handleTargetRunway = useCallback(
    async (ownerPlayerId: string) => {
      if (!isTargeting || !selectedAircraftId) return
      const isLegal = legalRunwayTargetIds.includes(ownerPlayerId)
      if (!isLegal) return
      await onAction({
        action_type: 'attack_aircraft',
        actor_player_id: myPlayerId,
        attacking_aircraft_id: selectedAircraftId,
        target: { target_type: 'runway', target_id: ownerPlayerId },
      })
      cancelTargeting()
    },
    [isTargeting, selectedAircraftId, legalRunwayTargetIds, myPlayerId, onAction, cancelTargeting],
  )

  const handleSelectAttacker = useCallback(
    async (aircraftId: string) => {
      setSelectedAircraftId(aircraftId)
      setIsTargeting(true)
      setLegalTargets([])
      const preview = await onPreviewAttack(aircraftId)
      if (preview) {
        setLegalTargets(preview.legal_targets)
      }
    },
    [onPreviewAttack],
  )

  const handleAttackFromPanel = useCallback(
    async (
      attackerId: string,
      target: { target_type: AttackTargetType; target_id: string },
    ) => {
      await onAction({
        action_type: 'attack_aircraft',
        actor_player_id: myPlayerId,
        attacking_aircraft_id: attackerId,
        target,
      })
      cancelTargeting()
    },
    [myPlayerId, onAction, cancelTargeting],
  )

  if (!myPlayer || !opponentPlayer) {
    return (
      <div className="min-h-screen bg-surface text-white flex items-center justify-center font-mono text-accent-muted">
        Loading board...
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-surface text-white flex flex-col">
      {/* Top bar with back button and match info */}
      <div className="flex items-center gap-3 px-4 py-1.5 bg-surface border-b border-surface-border">
        <button
          onClick={onBack}
          className="text-xs font-mono text-accent-muted hover:text-white transition-colors"
        >
          &larr; Lobby
        </button>
        <span className="text-xs font-mono text-surface-border">|</span>
        <span className="text-xs font-mono text-accent-muted">
          Match: <span className="text-white">{match.match_id.slice(0, 16)}...</span>
        </span>
      </div>

      {/* Phase bar */}
      <PhaseBar
        turnNumber={match.turn_number}
        phase={match.phase}
        activePlayerId={match.active_player_id}
        players={match.players}
        myPlayerId={myPlayerId}
        isTerminal={match.is_terminal}
        winnerPlayerId={match.winner_player_id}
      />

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-red-900/40 border-b border-accent-red font-mono text-accent-red text-xs">
          {error}
        </div>
      )}

      {/* Main board area — scrollable */}
      <div className="flex-1 overflow-auto flex flex-col">
        {/* Opponent zone (top) */}
        <div className="p-4 border-b border-surface-border">
          <PlayerZone
            player={opponentPlayer}
            isOpponent={true}
            selectedAircraftId={selectedAircraftId}
            legalTargetIds={legalTargetIds}
            legalActorIds={[]}
            legalRunwayTargetIds={legalRunwayTargetIds}
            onSelectAircraft={(id) => handleSelectAircraftOnBoard(id, opponentPlayer.player_id)}
            onTargetRunway={() => handleTargetRunway(opponentPlayer.player_id)}
          />
        </div>

        {/* Active buffs / hazards strip */}
        {(match.active_buffs.length > 0 || match.active_hazards.length > 0) && (
          <div className="px-4 py-2 bg-surface-elevated border-b border-surface-border flex flex-wrap gap-2">
            {match.active_buffs.map((b) => (
              <div
                key={b.buff_id}
                className="text-[10px] font-mono text-accent-blue border border-accent-blue/40 px-2 py-0.5 rounded"
              >
                BUFF: {b.source} → {b.description}
              </div>
            ))}
            {match.active_hazards.map((h) => (
              <div
                key={h.hazard_id}
                className="text-[10px] font-mono text-accent-red border border-accent-red/40 px-2 py-0.5 rounded"
              >
                HAZARD: {h.name}
              </div>
            ))}
          </div>
        )}

        {/* My zone (bottom) */}
        <div className="p-4 flex-1">
          <PlayerZone
            player={myPlayer}
            isOpponent={false}
            selectedAircraftId={selectedAircraftId}
            legalTargetIds={[]}
            legalActorIds={[]}
            legalRunwayTargetIds={[]}
            onSelectAircraft={(id) => handleSelectAircraftOnBoard(id, myPlayer.player_id)}
            onTargetRunway={() => {}}
          />
        </div>
      </div>

      {/* Action Panel */}
      <ActionPanel
        match={match}
        myPlayerId={myPlayerId}
        selectedAircraftId={selectedAircraftId}
        legalTargets={legalTargets}
        isTargeting={isTargeting}
        onLaunch={(aircraftId) =>
          onAction({ action_type: 'launch_aircraft', player_id: myPlayerId, aircraft_id: aircraftId })
        }
        onRefit={(aircraftId) =>
          onAction({ action_type: 'refit_aircraft', player_id: myPlayerId, aircraft_id: aircraftId })
        }
        onReturnToRunway={(aircraftId) =>
          onAction({
            action_type: 'return_to_runway',
            player_id: myPlayerId,
            aircraft_id: aircraftId,
          })
        }
        onSelectAttacker={handleSelectAttacker}
        onAttack={handleAttackFromPanel}
        onPlayOperation={(operationName, aircraftId) =>
          onAction({
            action_type: 'play_operation',
            player_id: myPlayerId,
            operation_name: operationName,
            aircraft_id: aircraftId,
          })
        }
        onPlayHazard={(hazardName) =>
          onAction({ action_type: 'play_hazard', player_id: myPlayerId, hazard_name: hazardName })
        }
        onAdvancePhase={onAdvancePhase}
        onCancelTargeting={cancelTargeting}
      />

      {/* Event log */}
      <EventLog events={match.event_history} players={match.players} />
    </div>
  )
}
