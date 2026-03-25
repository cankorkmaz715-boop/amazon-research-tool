/** Steps 246–248: Opportunity trend timeline – timeline_points, score_changes, rank_changes, observed_timestamps. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { OpportunityTimelineData } from '../../types/api'

const panelStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
}

export interface OpportunityTimelineProps {
  workspaceId: number
  opportunityId: number
}

export default function OpportunityTimeline({ workspaceId, opportunityId }: OpportunityTimelineProps) {
  const [data, setData] = useState<OpportunityTimelineData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api.getOpportunityTimeline(workspaceId, opportunityId)
      .then((res) => { if (!cancelled && res?.data) setData(res.data) })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [workspaceId, opportunityId])

  if (loading) return <div style={panelStyle}>Loading timeline…</div>
  if (error) return <div style={{ ...panelStyle, color: '#b91c1c' }}>{error}</div>
  if (!data) return <div style={panelStyle}>No timeline data.</div>

  const points = data.timeline_points ?? []
  const scoreChanges = data.score_changes ?? []
  const rankChanges = data.rank_changes ?? []
  const timestamps = data.observed_timestamps ?? []

  return (
    <div style={panelStyle} data-testid="opportunity-timeline">
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Opportunity timeline</h3>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#666' }}>
        {timestamps.length} observed timestamp(s)
      </p>
      {points.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <strong style={{ fontSize: '0.85rem' }}>Timeline points:</strong>
          <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
            {points.slice(0, 10).map((p, i) => (
              <li key={i}>{p.observed_at ?? '—'} — score: {p.score ?? '—'}, rank: {p.rank ?? '—'}</li>
            ))}
            {points.length > 10 && <li>… and {points.length - 10} more</li>}
          </ul>
        </div>
      )}
      {scoreChanges.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <strong style={{ fontSize: '0.85rem' }}>Score changes:</strong>
          <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
            {scoreChanges.slice(0, 5).map((s, i) => (
              <li key={i}>{s.at ?? '—'} → {s.score ?? '—'}</li>
            ))}
          </ul>
        </div>
      )}
      {rankChanges.length > 0 && (
        <div>
          <strong style={{ fontSize: '0.85rem' }}>Rank changes:</strong>
          <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
            {rankChanges.slice(0, 5).map((r, i) => (
              <li key={i}>{r.at ?? '—'} → {r.rank ?? '—'}</li>
            ))}
          </ul>
        </div>
      )}
      {points.length === 0 && scoreChanges.length === 0 && rankChanges.length === 0 && (
        <p style={{ margin: 0, fontSize: '0.875rem', color: '#666' }}>No timeline points yet.</p>
      )}
    </div>
  )
}
