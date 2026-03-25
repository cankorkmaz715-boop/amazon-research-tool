/** Steps 243–245: Keyword opportunity clusters page. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { DiscoveryCluster } from '../../types/api'
import DiscoveryClusterCard from '../../components/discovery/DiscoveryClusterCard'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
}

export interface DiscoveryClustersPageProps {
  workspaceId: number
}

export default function DiscoveryClustersPage({ workspaceId }: DiscoveryClustersPageProps) {
  const [clusters, setClusters] = useState<DiscoveryCluster[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .getDiscoveryClusters(workspaceId)
      .then((res) => { if (!cancelled && res?.data) setClusters(Array.isArray(res.data) ? res.data : []) })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [workspaceId])

  if (loading) return <div style={cardStyle}>Loading clusters…</div>
  if (error) return <div style={{ ...cardStyle, color: '#b91c1c' }}>{error}</div>
  if (clusters.length === 0) return <div style={cardStyle}>No clusters.</div>
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Keyword opportunity clusters</h2>
      {clusters.map((c, i) => (
        <DiscoveryClusterCard key={c.cluster_id ?? i} cluster={c} />
      ))}
    </div>
  )
}
