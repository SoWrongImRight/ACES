import { useState } from 'react'
import { MatchBoard } from './components/board/MatchBoard'
import { MatchList } from './components/lobby/MatchList'
import { useMatch } from './hooks/useMatch'

type View = 'lobby' | 'player-select' | 'board'

export default function App() {
  const [view, setView] = useState<View>('lobby')
  const [matchId, setMatchId] = useState<string | null>(null)

  const { match, error, loading, myPlayerId, setMyPlayerId, doAction, doAdvancePhase, previewAttackTargets } =
    useMatch(matchId)

  function handleEnterMatch(id: string) {
    setMatchId(id)
    setView('player-select')
  }

  function handleSelectPlayer(playerId: string) {
    setMyPlayerId(playerId)
    setView('board')
  }

  function handleBack() {
    setMatchId(null)
    setView('lobby')
  }

  // ── Lobby ──────────────────────────────────────────────────────────────────
  if (view === 'lobby') {
    return <MatchList onEnterMatch={handleEnterMatch} />
  }

  // ── Player select ──────────────────────────────────────────────────────────
  if (view === 'player-select') {
    return (
      <div className="min-h-screen bg-surface text-white flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold tracking-[0.3em] font-mono text-accent-green uppercase mb-1">
              A.C.E.S.
            </h1>
            <p className="text-accent-muted text-sm font-mono">Select your side</p>
          </div>

          {loading && (
            <div className="text-center text-accent-muted font-mono text-sm mb-4">
              Loading match...
            </div>
          )}

          {error && (
            <div className="mb-4 p-3 bg-red-900/40 border border-accent-red rounded font-mono text-accent-red text-sm">
              {error}
            </div>
          )}

          {match && (
            <div className="flex flex-col gap-3">
              <div className="text-xs font-mono text-accent-muted text-center mb-2">
                Match: {match.match_id.slice(0, 24)}...
              </div>
              {match.players.map((p, i) => (
                <button
                  key={p.player_id}
                  onClick={() => handleSelectPlayer(p.player_id)}
                  className="w-full border border-surface-border bg-surface-card rounded-lg px-5 py-4
                             hover:border-accent-green hover:bg-surface-elevated transition-all group"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-left">
                      <div className="font-mono font-bold text-white group-hover:text-accent-green transition-colors">
                        Player {i + 1}: {p.display_name}
                      </div>
                      <div className="font-mono text-xs text-accent-muted mt-0.5">
                        {p.aircraft.length} aircraft &mdash; RWY {p.runway.health}/{p.runway.max_health}
                      </div>
                    </div>
                    <span className="text-accent-muted group-hover:text-accent-green font-mono text-sm transition-colors">
                      Play &rarr;
                    </span>
                  </div>
                </button>
              ))}
              <button
                onClick={handleBack}
                className="mt-2 text-xs font-mono text-accent-muted hover:text-white transition-colors"
              >
                &larr; Back to lobby
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Board ──────────────────────────────────────────────────────────────────
  if (view === 'board' && match && myPlayerId) {
    return (
      <MatchBoard
        match={match}
        myPlayerId={myPlayerId}
        error={error}
        onAction={doAction}
        onAdvancePhase={doAdvancePhase}
        onPreviewAttack={previewAttackTargets}
        onBack={handleBack}
      />
    )
  }

  // Fallback while loading board
  return (
    <div className="min-h-screen bg-surface text-white flex items-center justify-center font-mono text-accent-muted">
      Loading...
    </div>
  )
}
