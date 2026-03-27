import { useState } from 'react'
import type {
  AttackTargetType,
  LegalTarget,
  MatchStateResponse,
  Phase,
} from '../../api/types'

const OPERATIONS = ['resupply', 'target-lock', 'afterburner', 'full-send'] as const
const HAZARDS = ['flak-burst', 'missile-jam', 'crosswind'] as const

interface Props {
  match: MatchStateResponse
  myPlayerId: string
  selectedAircraftId: string | null
  legalTargets: LegalTarget[]
  isTargeting: boolean
  onLaunch: (aircraftId: string) => void
  onRefit: (aircraftId: string) => void
  onReturnToRunway: (aircraftId: string) => void
  onSelectAttacker: (aircraftId: string) => void
  onAttack: (attackerId: string, target: { target_type: AttackTargetType; target_id: string }) => void
  onPlayOperation: (operationName: string, aircraftId: string) => void
  onPlayHazard: (hazardName: string) => void
  onAdvancePhase: () => void
  onCancelTargeting: () => void
}

export function ActionPanel({
  match,
  myPlayerId,
  selectedAircraftId,
  legalTargets,
  isTargeting,
  onLaunch,
  onRefit,
  onReturnToRunway,
  onSelectAttacker,
  onAttack,
  onPlayOperation,
  onPlayHazard,
  onAdvancePhase,
  onCancelTargeting,
}: Props) {
  const [selectedOperation, setSelectedOperation] = useState<string>(OPERATIONS[0])
  const [operationAircraftId, setOperationAircraftId] = useState<string>('')
  const [selectedHazard, setSelectedHazard] = useState<string>(HAZARDS[0])

  const { phase, active_player_id, is_terminal } = match
  const isMyTurn = active_player_id === myPlayerId
  const myPlayer = match.players.find((p) => p.player_id === myPlayerId)
  const opponentPlayer = match.players.find((p) => p.player_id !== myPlayerId)

  if (!myPlayer) return null

  const myAircraft = myPlayer.aircraft.filter((a) => !a.destroyed)
  const runwayAircraft = myAircraft.filter((a) => a.zone === 'runway')
  const airAircraft = myAircraft.filter((a) => a.zone === 'air')

  function renderAdvancePhaseBtn() {
    const disabled = is_terminal || !isMyTurn
    return (
      <button
        onClick={onAdvancePhase}
        disabled={disabled}
        className="w-full font-mono text-sm font-bold py-2 px-4 rounded border
                   border-accent-muted text-accent-muted
                   hover:border-white hover:text-white
                   disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        Advance Phase &rarr;
      </button>
    )
  }

  function renderCommandPhase() {
    return (
      <div className="flex flex-col gap-3">
        {isMyTurn && (
          <div className="flex flex-col gap-2">
            <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
              Play Operation
            </div>
            <div className="flex gap-2 flex-wrap">
              <select
                value={selectedOperation}
                onChange={(e) => setSelectedOperation(e.target.value)}
                className="bg-surface-elevated border border-surface-border text-white font-mono text-xs px-2 py-1.5 rounded"
              >
                {OPERATIONS.map((op) => (
                  <option key={op} value={op}>
                    {op}
                  </option>
                ))}
              </select>
              <select
                value={operationAircraftId}
                onChange={(e) => setOperationAircraftId(e.target.value)}
                className="bg-surface-elevated border border-surface-border text-white font-mono text-xs px-2 py-1.5 rounded flex-1"
              >
                <option value="">-- select aircraft --</option>
                {myAircraft.map((a) => (
                  <option key={a.aircraft_id} value={a.aircraft_id}>
                    {a.name}
                  </option>
                ))}
              </select>
              <button
                onClick={() => {
                  if (operationAircraftId) {
                    onPlayOperation(selectedOperation, operationAircraftId)
                  }
                }}
                disabled={!operationAircraftId}
                className="bg-accent-blue text-surface font-bold font-mono text-xs py-1.5 px-3 rounded
                           disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-300 transition-colors"
              >
                Play
              </button>
            </div>
          </div>
        )}

        {/* Hazard for non-active player */}
        {!isMyTurn && (
          <div className="flex flex-col gap-2">
            <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
              Play Hazard (responding)
            </div>
            <div className="flex gap-2 flex-wrap">
              <select
                value={selectedHazard}
                onChange={(e) => setSelectedHazard(e.target.value)}
                className="bg-surface-elevated border border-surface-border text-white font-mono text-xs px-2 py-1.5 rounded"
              >
                {HAZARDS.map((h) => (
                  <option key={h} value={h}>
                    {h}
                  </option>
                ))}
              </select>
              <button
                onClick={() => onPlayHazard(selectedHazard)}
                className="bg-accent-red text-surface font-bold font-mono text-xs py-1.5 px-3 rounded
                           hover:bg-red-300 transition-colors"
              >
                Play Hazard
              </button>
            </div>
          </div>
        )}

        {renderAdvancePhaseBtn()}
      </div>
    )
  }

  function renderGroundPhase() {
    return (
      <div className="flex flex-col gap-3">
        {isMyTurn && runwayAircraft.length > 0 && (
          <div className="flex flex-col gap-2">
            <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
              Ground Actions
            </div>
            <div className="flex flex-wrap gap-2">
              {runwayAircraft.map((ac) => (
                <div
                  key={ac.aircraft_id}
                  className="flex items-center gap-1.5 bg-surface-elevated border border-surface-border rounded px-2 py-1.5"
                >
                  <span className="text-xs font-mono text-white">{ac.name}</span>
                  <button
                    onClick={() => onRefit(ac.aircraft_id)}
                    disabled={ac.refit_this_turn}
                    title={ac.refit_this_turn ? 'Already refitted this turn' : 'Refit this aircraft'}
                    className="text-[10px] font-mono font-bold text-accent-amber border border-accent-amber/50
                               px-1.5 py-0.5 rounded disabled:opacity-30 disabled:cursor-not-allowed
                               hover:bg-accent-amber hover:text-surface transition-colors"
                  >
                    REFIT
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
        {isMyTurn && runwayAircraft.length === 0 && (
          <div className="text-xs font-mono text-accent-muted italic">No aircraft on runway.</div>
        )}
        {!isMyTurn && (
          <div className="text-xs font-mono text-accent-muted italic">Opponent&apos;s ground phase.</div>
        )}
        {renderAdvancePhaseBtn()}
      </div>
    )
  }

  function renderAirPhase() {
    const selectedAc = selectedAircraftId
      ? myAircraft.find((a) => a.aircraft_id === selectedAircraftId)
      : null

    return (
      <div className="flex flex-col gap-3">
        {isTargeting && selectedAc ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="text-[10px] font-mono text-accent-amber uppercase tracking-widest">
                Targeting with {selectedAc.name}
              </div>
              <button
                onClick={onCancelTargeting}
                className="text-[10px] font-mono text-accent-muted hover:text-white transition-colors"
              >
                Cancel
              </button>
            </div>
            {legalTargets.length === 0 ? (
              <div className="text-xs font-mono text-accent-muted italic">
                No legal targets — advance or cancel.
              </div>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {legalTargets.map((t) => {
                  const targetName =
                    t.target_type === 'runway'
                      ? `${opponentPlayer?.display_name ?? 'Opponent'} Runway`
                      : match.players
                          .flatMap((p) => p.aircraft)
                          .find((a) => a.aircraft_id === t.target_id)?.name ?? t.target_id
                  return (
                    <button
                      key={`${t.target_type}:${t.target_id}`}
                      onClick={() =>
                        onAttack(selectedAircraftId!, {
                          target_type: t.target_type,
                          target_id: t.target_id,
                        })
                      }
                      className="text-xs font-mono font-bold text-surface bg-accent-amber px-3 py-1 rounded
                                 hover:bg-amber-300 transition-colors"
                    >
                      Attack {targetName}
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        ) : (
          isMyTurn && (
            <div className="flex flex-col gap-2">
              <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
                Air Actions
              </div>

              {/* Runway aircraft: launch */}
              {runwayAircraft.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {runwayAircraft.map((ac) => (
                    <div
                      key={ac.aircraft_id}
                      className="flex items-center gap-1.5 bg-surface-elevated border border-surface-border rounded px-2 py-1.5"
                    >
                      <span className="text-xs font-mono text-white">{ac.name}</span>
                      <button
                        onClick={() => onLaunch(ac.aircraft_id)}
                        disabled={ac.refit_this_turn}
                        title={ac.refit_this_turn ? 'Refitted — cannot launch this turn' : 'Launch to air'}
                        className="text-[10px] font-mono font-bold text-accent-green border border-accent-green/50
                                   px-1.5 py-0.5 rounded disabled:opacity-30 disabled:cursor-not-allowed
                                   hover:bg-accent-green hover:text-surface transition-colors"
                      >
                        LAUNCH
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Air aircraft: attack or return */}
              {airAircraft.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {airAircraft.map((ac) => (
                    <div
                      key={ac.aircraft_id}
                      className="flex items-center gap-1.5 bg-surface-elevated border border-surface-border rounded px-2 py-1.5"
                    >
                      <span className="text-xs font-mono text-white">{ac.name}</span>
                      <button
                        onClick={() => onSelectAttacker(ac.aircraft_id)}
                        disabled={ac.has_attacked_this_phase || ac.exhausted}
                        title={
                          ac.has_attacked_this_phase
                            ? 'Already attacked'
                            : ac.exhausted
                              ? 'Exhausted'
                              : 'Select attacker'
                        }
                        className="text-[10px] font-mono font-bold text-accent-amber border border-accent-amber/50
                                   px-1.5 py-0.5 rounded disabled:opacity-30 disabled:cursor-not-allowed
                                   hover:bg-accent-amber hover:text-surface transition-colors"
                      >
                        ATTACK
                      </button>
                      <button
                        onClick={() => onReturnToRunway(ac.aircraft_id)}
                        className="text-[10px] font-mono text-accent-muted border border-surface-border
                                   px-1.5 py-0.5 rounded hover:text-white hover:border-white transition-colors"
                      >
                        RTB
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {airAircraft.length === 0 && runwayAircraft.length === 0 && (
                <div className="text-xs font-mono text-accent-muted italic">No aircraft available.</div>
              )}
            </div>
          )
        )}

        {!isMyTurn && !isTargeting && (
          <div className="text-xs font-mono text-accent-muted italic">Opponent&apos;s air phase.</div>
        )}

        {renderAdvancePhaseBtn()}
      </div>
    )
  }

  function renderEndPhase() {
    return (
      <div className="flex flex-col gap-2">
        {!isMyTurn && (
          <div className="text-xs font-mono text-accent-muted italic">Waiting for opponent to end turn.</div>
        )}
        {renderAdvancePhaseBtn()}
      </div>
    )
  }

  const phaseRenderers: Record<Phase, () => React.ReactNode> = {
    command: renderCommandPhase,
    ground: renderGroundPhase,
    air: renderAirPhase,
    end: renderEndPhase,
  }

  return (
    <div className="border-t border-surface-border bg-surface-card px-4 py-3">
      <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest mb-2">
        Actions
      </div>
      {phaseRenderers[phase]?.()}
    </div>
  )
}
