/**
 * Pipeline: Watch / unwatch opportunity. Optimistic UI update.
 */
import { useState } from 'react'
import { api } from '../../lib/api'

export interface OpportunityWatchButtonProps {
  workspaceId: number
  opportunityId: number
  initiallyWatched?: boolean
  onWatchChange?: (watched: boolean) => void
}

export default function OpportunityWatchButton({
  workspaceId,
  opportunityId,
  initiallyWatched = false,
  onWatchChange,
}: OpportunityWatchButtonProps) {
  const [watched, setWatched] = useState(initiallyWatched)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleToggle = async () => {
    setLoading(true)
    setError(null)
    const next = !watched
    setWatched(next)
    try {
      if (next) {
        await api.postOpportunityWatch(workspaceId, opportunityId)
      } else {
        await api.deleteOpportunityWatch(workspaceId, opportunityId)
      }
      onWatchChange?.(next)
    } catch (e) {
      setWatched(!next)
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleToggle}
        disabled={loading}
        style={{ padding: '0.5rem 1rem', cursor: loading ? 'not-allowed' : 'pointer' }}
      >
        {loading ? '…' : watched ? 'Unwatch' : 'Add to watchlist'}
      </button>
      {error && <span style={{ marginLeft: '0.5rem', fontSize: '0.85rem', color: '#b91c1c' }}>{error}</span>}
    </div>
  )
}
