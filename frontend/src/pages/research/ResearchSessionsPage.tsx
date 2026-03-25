/** Steps 249–250: Research sessions page – list and create. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { ResearchSession } from '../../types/api'
import ResearchSessionCard from '../../components/research/ResearchSessionCard'

const pageStyle: React.CSSProperties = { marginBottom: '1rem' }
const cardStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
}

export interface ResearchSessionsPageProps {
  workspaceId: number
}

export default function ResearchSessionsPage({ workspaceId }: ResearchSessionsPageProps) {
  const [sessions, setSessions] = useState<ResearchSession[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [label, setLabel] = useState('')

  const load = () => {
    setLoading(true)
    setError(null)
    api.getResearchSessions(workspaceId)
      .then((res) => { if (res?.data) setSessions(Array.isArray(res.data) ? res.data : []) })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [workspaceId])

  const handleCreate = () => {
    api.postResearchSession(workspaceId, { label: label.trim() || 'New session' })
      .then(() => { setLabel(''); load() })
      .catch((e) => setError(e instanceof Error ? e.message : 'Create failed'))
  }

  if (loading && sessions.length === 0) {
    return <div style={cardStyle}>Loading research sessions…</div>
  }

  return (
    <div style={pageStyle}>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Research sessions</h2>
      {error && <p style={{ color: '#b91c1c', margin: '0 0 0.5rem', fontSize: '0.875rem' }}>{error}</p>}
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
        <input
          placeholder="Session label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          style={{ padding: '0.35rem', minWidth: 200 }}
        />
        <button type="button" onClick={handleCreate} style={{ padding: '0.35rem 0.75rem' }}>
          New session
        </button>
      </div>
      {sessions.length === 0 && !loading && (
        <p style={{ fontSize: '0.875rem', color: '#666' }}>No research sessions yet.</p>
      )}
      {sessions.map((s) => (
        <ResearchSessionCard key={s.id ?? 0} session={s} />
      ))}
    </div>
  )
}
