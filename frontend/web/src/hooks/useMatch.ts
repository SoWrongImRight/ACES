import { useCallback, useEffect, useRef, useState } from 'react'
import {
  advancePhase,
  executeAction,
  getMatch,
  previewAttack,
} from '../api/client'
import type {
  ActionBody,
  ActionValidationResponse,
  MatchStateResponse,
} from '../api/types'

const POLL_INTERVAL_MS = 2000

interface UseMatchResult {
  match: MatchStateResponse | null
  error: string | null
  loading: boolean
  myPlayerId: string | null
  setMyPlayerId: (id: string) => void
  doAction: (body: ActionBody) => Promise<void>
  doAdvancePhase: () => Promise<void>
  previewAttackTargets: (
    aircraftId: string,
  ) => Promise<ActionValidationResponse | null>
}

export function useMatch(matchId: string | null): UseMatchResult {
  const [match, setMatch] = useState<MatchStateResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [myPlayerId, setMyPlayerId] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchMatch = useCallback(async () => {
    if (!matchId) return
    try {
      const state = await getMatch(matchId)
      setMatch(state)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch match')
    }
  }, [matchId])

  // Initial load
  useEffect(() => {
    if (!matchId) return
    setLoading(true)
    fetchMatch().finally(() => setLoading(false))
  }, [matchId, fetchMatch])

  // Polling
  useEffect(() => {
    if (!matchId) return
    pollRef.current = setInterval(() => {
      if (!document.hidden) {
        fetchMatch()
      }
    }, POLL_INTERVAL_MS)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [matchId, fetchMatch])

  const doAction = useCallback(
    async (body: ActionBody) => {
      if (!matchId) return
      try {
        const result = await executeAction(matchId, body)
        setMatch(result.match_state)
        setError(null)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Action failed')
      }
    },
    [matchId],
  )

  const doAdvancePhase = useCallback(async () => {
    if (!matchId || !myPlayerId) return
    try {
      const result = await advancePhase(matchId, myPlayerId)
      setMatch(result.match_state)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Advance phase failed')
    }
  }, [matchId, myPlayerId])

  const previewAttackTargets = useCallback(
    async (aircraftId: string): Promise<ActionValidationResponse | null> => {
      if (!matchId || !myPlayerId) return null
      try {
        return await previewAttack(matchId, myPlayerId, aircraftId)
      } catch {
        return null
      }
    },
    [matchId, myPlayerId],
  )

  return {
    match,
    error,
    loading,
    myPlayerId,
    setMyPlayerId,
    doAction,
    doAdvancePhase,
    previewAttackTargets,
  }
}

export type { UseMatchResult }
