import type { AircraftStateResponse, PlayerStateResponse } from '../../api/types'
import { AircraftCard } from './AircraftCard'
import { RunwayCard } from './RunwayCard'

interface Props {
  player: PlayerStateResponse
  isOpponent: boolean
  selectedAircraftId: string | null
  legalTargetIds: string[]
  legalActorIds: string[]
  legalRunwayTargetIds: string[]
  onSelectAircraft: (id: string) => void
  onTargetRunway: () => void
}

export function PlayerZone({
  player,
  isOpponent,
  selectedAircraftId,
  legalTargetIds,
  legalActorIds,
  legalRunwayTargetIds,
  onSelectAircraft,
  onTargetRunway,
}: Props) {
  const airAircraft = player.aircraft.filter((a) => a.zone === 'air')
  const groundAircraft = player.aircraft.filter((a) => a.zone === 'runway')

  const runwayIsLegalTarget = legalRunwayTargetIds.includes(player.player_id)

  function renderAircraft(ac: AircraftStateResponse) {
    return (
      <AircraftCard
        key={ac.aircraft_id}
        aircraft={ac}
        isSelected={selectedAircraftId === ac.aircraft_id}
        isLegalTarget={legalTargetIds.includes(ac.aircraft_id)}
        isLegalActor={legalActorIds.includes(ac.aircraft_id)}
        onClick={() => onSelectAircraft(ac.aircraft_id)}
        flipped={isOpponent}
      />
    )
  }

  // Opponent layout: air zone left, runway right (mirrored from player's perspective)
  // Player layout: runway left, air zone right
  const zones = isOpponent ? (
    <>
      {/* Opponent: Air Zone | Runway */}
      <div className="flex-1 flex flex-col">
        <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest mb-1.5 px-1">
          Air Zone
        </div>
        <div className="flex flex-wrap gap-2 min-h-[100px] items-start">
          {airAircraft.length === 0 ? (
            <div className="text-[10px] font-mono text-surface-border italic">Empty</div>
          ) : (
            airAircraft.map(renderAircraft)
          )}
        </div>
      </div>
      <div className="w-px bg-surface-border self-stretch mx-2" />
      <div className="flex flex-col items-end gap-2">
        <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest mb-1.5 px-1 self-start">
          Runway
        </div>
        <div className="flex flex-wrap gap-2 justify-end min-h-[100px] items-start">
          <RunwayCard
            runway={player.runway}
            isLegalTarget={runwayIsLegalTarget}
            isSelected={false}
            onClick={onTargetRunway}
            flipped={isOpponent}
          />
          {groundAircraft.map(renderAircraft)}
        </div>
      </div>
    </>
  ) : (
    <>
      {/* Player: Runway | Air Zone */}
      <div className="flex flex-col items-start gap-2">
        <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest mb-1.5 px-1">
          Runway
        </div>
        <div className="flex flex-wrap gap-2 min-h-[100px] items-start">
          <RunwayCard
            runway={player.runway}
            isLegalTarget={runwayIsLegalTarget}
            isSelected={false}
            onClick={onTargetRunway}
          />
          {groundAircraft.map(renderAircraft)}
        </div>
      </div>
      <div className="w-px bg-surface-border self-stretch mx-2" />
      <div className="flex-1 flex flex-col">
        <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest mb-1.5 px-1">
          Air Zone
        </div>
        <div className="flex flex-wrap gap-2 min-h-[100px] items-start">
          {airAircraft.length === 0 ? (
            <div className="text-[10px] font-mono text-surface-border italic">Empty</div>
          ) : (
            airAircraft.map(renderAircraft)
          )}
        </div>
      </div>
    </>
  )

  return (
    <div className="flex flex-col gap-1">
      {/* Player header */}
      <div className="flex items-center justify-between px-1 mb-1">
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-bold font-mono ${isOpponent ? 'text-accent-red' : 'text-accent-green'}`}
          >
            {isOpponent ? 'ENEMY' : 'YOU'}
          </span>
          <span className="text-xs font-mono text-white">{player.display_name}</span>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono text-accent-muted">
          <span>
            RWY{' '}
            <span className="text-white">
              {player.runway.health}/{player.runway.max_health}
            </span>
          </span>
          <span>
            HAND <span className="text-white">{player.hand_size}</span>
          </span>
        </div>
      </div>

      {/* Zones row */}
      <div className="flex items-start gap-0">{zones}</div>
    </div>
  )
}
