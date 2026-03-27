import type { AircraftStateResponse } from '../../api/types'

interface Props {
  aircraft: AircraftStateResponse
  isSelected: boolean
  isLegalTarget: boolean
  isLegalActor: boolean
  onClick: () => void
  flipped?: boolean
}

export function AircraftCard({
  aircraft,
  isSelected,
  isLegalTarget,
  isLegalActor,
  onClick,
  flipped,
}: Props) {
  const srMax = aircraft.max_structure_rating ?? aircraft.structure_rating
  const srPct = Math.max(0, aircraft.structure_rating / srMax)
  const fuelPct = aircraft.max_fuel > 0 ? aircraft.fuel / aircraft.max_fuel : 0

  const srColor =
    srPct > 0.6 ? 'bg-accent-green' : srPct > 0.3 ? 'bg-accent-amber' : 'bg-accent-red'

  const borderClass = isSelected
    ? 'border-accent-green ring-2 ring-accent-green/40'
    : isLegalTarget
      ? 'border-accent-amber shadow-[0_0_8px_rgba(251,191,36,0.4)] animate-pulse'
      : isLegalActor
        ? 'border-accent-blue shadow-[0_0_6px_rgba(96,165,250,0.3)]'
        : aircraft.destroyed
          ? 'border-surface-border opacity-40'
          : aircraft.exhausted
            ? 'border-surface-border opacity-60'
            : 'border-surface-border'

  const content = (
    <>
      {/* Zone badge */}
      <div className="flex items-center justify-between w-full mb-1">
        <span
          className={`text-[9px] font-mono uppercase tracking-widest ${
            aircraft.zone === 'air' ? 'text-accent-blue' : 'text-accent-muted'
          }`}
        >
          {aircraft.zone}
        </span>
        {aircraft.exhausted && !aircraft.destroyed && (
          <span className="text-[9px] font-mono text-accent-amber uppercase">EXH</span>
        )}
        {aircraft.destroyed && (
          <span className="text-[9px] font-mono text-accent-red uppercase">KIA</span>
        )}
        {aircraft.has_attacked_this_phase && !aircraft.destroyed && (
          <span className="text-[9px] font-mono text-accent-muted uppercase">ATK</span>
        )}
      </div>

      {/* Name */}
      <div className="text-xs font-bold font-mono text-white leading-tight text-center mb-1.5 truncate w-full">
        {aircraft.name}
      </div>

      {/* SR bar */}
      <div className="w-full mb-1">
        <div className="flex justify-between text-[9px] font-mono text-accent-muted mb-0.5">
          <span>SR</span>
          <span>
            {aircraft.structure_rating}/{srMax}
          </span>
        </div>
        <div className="w-full h-1 bg-surface-border rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${srColor}`}
            style={{ width: `${srPct * 100}%` }}
          />
        </div>
      </div>

      {/* Fuel bar */}
      <div className="w-full mb-1.5">
        <div className="flex justify-between text-[9px] font-mono text-accent-muted mb-0.5">
          <span>FUEL</span>
          <span>
            {aircraft.fuel}/{aircraft.max_fuel}
          </span>
        </div>
        <div className="w-full h-1 bg-surface-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all bg-accent-blue"
            style={{ width: `${fuelPct * 100}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="flex justify-between w-full text-[10px] font-mono">
        <span>
          <span className="text-accent-muted">ATK </span>
          <span className="text-accent-green font-bold">{aircraft.attack}</span>
        </span>
        <span>
          <span className="text-accent-muted">EVD </span>
          <span className="text-accent-blue font-bold">{aircraft.evasion}</span>
        </span>
      </div>

      {/* Pilot */}
      {aircraft.pilot && (
        <div className="mt-1.5 w-full border-t border-surface-border pt-1">
          <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest">
            Pilot
          </div>
          <div className="text-[10px] font-mono text-white truncate">{aircraft.pilot.name}</div>
        </div>
      )}

      {/* Weapon */}
      {aircraft.weapon && (
        <div className="mt-1 w-full border-t border-surface-border pt-1">
          <div className="text-[9px] font-mono text-accent-muted uppercase tracking-widest">
            Weapon
          </div>
          <div
            className={`text-[10px] font-mono truncate ${
              aircraft.weapon.exhausted ? 'text-accent-muted line-through' : 'text-accent-amber'
            }`}
          >
            {aircraft.weapon.name}
            {aircraft.weapon.exhausted && ' (EXH)'}
          </div>
        </div>
      )}
    </>
  )

  return (
    <div
      onClick={!aircraft.destroyed ? onClick : undefined}
      className={[
        'relative w-28 rounded border bg-surface-card px-2 py-2 flex flex-col items-center',
        aircraft.destroyed ? '' : 'cursor-pointer hover:bg-surface-elevated',
        borderClass,
        'transition-all duration-150 select-none',
        flipped ? 'flex-col-reverse' : '',
      ].join(' ')}
    >
      {isLegalTarget && (
        <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-accent-amber" />
      )}
      {isLegalActor && !isSelected && (
        <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-accent-blue" />
      )}
      {content}
    </div>
  )
}
