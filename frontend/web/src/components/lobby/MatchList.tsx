import { useEffect, useState } from 'react'
import { createMatch, listMatches } from '../../api/client'
import type { MatchListItem } from '../../api/types'

interface Props {
  onEnterMatch: (matchId: string) => void
}

export function MatchList({ onEnterMatch }: Props) {
  const [matches, setMatches] = useState<MatchListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    try {
      const res = await listMatches()
      setMatches(res.matches)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load matches')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function handleCreate() {
    setCreating(true)
    try {
      const res = await createMatch()
      onEnterMatch(res.match_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create match')
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface text-white flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold tracking-[0.3em] font-mono text-accent-green uppercase mb-1">
            A.C.E.S.
          </h1>
          <p className="text-accent-muted text-sm tracking-widest uppercase font-mono">
            Tactical Air Combat
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={handleCreate}
            disabled={creating}
            className="flex-1 bg-accent-green text-surface font-bold font-mono py-3 px-6 rounded
                       hover:bg-green-300 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors uppercase tracking-widest text-sm"
          >
            {creating ? 'Creating...' : '+ New Match'}
          </button>
          <button
            onClick={refresh}
            className="bg-surface-elevated border border-surface-border text-accent-muted
                       font-mono py-3 px-4 rounded hover:text-white hover:border-accent-muted
                       transition-colors text-sm"
          >
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-900/40 border border-accent-red rounded font-mono text-accent-red text-sm">
            {error}
          </div>
        )}

        {/* Match List */}
        <div className="border border-surface-border rounded-lg overflow-hidden">
          <div className="bg-surface-elevated px-4 py-2 border-b border-surface-border">
            <span className="font-mono text-xs text-accent-muted uppercase tracking-widest">
              Active Matches
            </span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-accent-muted font-mono text-sm">
              Loading...
            </div>
          ) : matches.length === 0 ? (
            <div className="p-8 text-center text-accent-muted font-mono text-sm">
              No active matches. Create one to begin.
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {matches.map((m) => (
                <button
                  key={m.match_id}
                  onClick={() => onEnterMatch(m.match_id)}
                  className="w-full flex items-center justify-between px-4 py-3
                             hover:bg-surface-elevated transition-colors group text-left"
                >
                  <div>
                    <div className="font-mono text-sm text-white group-hover:text-accent-green transition-colors">
                      {m.match_id.slice(0, 16)}...
                    </div>
                    <div className="font-mono text-xs text-accent-muted mt-0.5">
                      Turn {m.turn_number} &mdash; Phase:{' '}
                      <span className="text-accent-amber uppercase">{m.phase}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {m.is_terminal && (
                      <span className="text-xs font-mono text-accent-red border border-accent-red/50 px-2 py-0.5 rounded">
                        ENDED
                      </span>
                    )}
                    <span className="text-accent-muted text-xs font-mono group-hover:text-white">
                      Enter &rarr;
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
