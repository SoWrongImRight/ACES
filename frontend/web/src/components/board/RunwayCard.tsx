import type { RunwayStateResponse } from '../../api/types'

interface Props {
  runway: RunwayStateResponse
  isLegalTarget: boolean
  isSelected: boolean
  onClick?: () => void
  flipped?: boolean
}

export function RunwayCard({ runway, isLegalTarget, isSelected, onClick, flipped }: Props) {
  const pct = Math.max(0, runway.health / runway.max_health)
  const barColor =
    pct > 0.6
      ? 'bg-accent-green'
      : pct > 0.3
        ? 'bg-accent-amber'
        : 'bg-accent-red'

  return (
    <div
      onClick={isLegalTarget ? onClick : undefined}
      className={[
        'relative w-20 rounded border flex flex-col items-center justify-center gap-1 px-2 py-3 select-none',
        flipped ? 'flex-col-reverse' : '',
        isLegalTarget
          ? 'border-accent-amber cursor-pointer shadow-[0_0_8px_rgba(251,191,36,0.5)] animate-pulse'
          : 'border-surface-border',
        isSelected ? 'ring-2 ring-accent-amber' : '',
        'bg-surface-card transition-all duration-150',
      ].join(' ')}
    >
      <div className="text-[10px] font-mono text-accent-muted uppercase tracking-widest">
        Runway
      </div>
      <div className="text-sm font-bold font-mono text-white">
        {runway.health}
        <span className="text-accent-muted text-xs">/{runway.max_health}</span>
      </div>
      {/* Health bar */}
      <div className="w-full h-1.5 bg-surface-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      {isLegalTarget && (
        <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-accent-amber" />
      )}
    </div>
  )
}
