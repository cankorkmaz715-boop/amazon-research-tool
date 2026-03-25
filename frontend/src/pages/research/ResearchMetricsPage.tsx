/** Steps 249–250: Research performance metrics page. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { ResearchMetrics } from '../../types/api'
import ResearchMetricsCards from '../../components/research/ResearchMetricsCards'

const cardStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
}

export interface ResearchMetricsPageProps {
  workspaceId: number
}

export default function ResearchMetricsPage({ workspaceId }: ResearchMetricsPageProps) {
  const [metrics, setMetrics] = useState<ResearchMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api.getResearchMetrics(workspaceId)
      .then((res) => { if (!cancelled && res?.data) setMetrics(res.data) })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [workspaceId])

  if (loading) return <div style={cardStyle}>Loading research metrics…</div>
  if (error) return <div style={{ ...cardStyle, color: '#b91c1c' }}>{error}</div>

  return (
    <div>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Research performance metrics</h2>
      <ResearchMetricsCards metrics={metrics} />
    </div>
  )
}
