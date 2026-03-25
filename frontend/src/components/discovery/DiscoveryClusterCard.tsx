/** Steps 243–245: Single cluster card. */
import type { DiscoveryCluster } from '../../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function DiscoveryClusterCard({ cluster }: { cluster: DiscoveryCluster }) {
  const id = cluster?.cluster_id ?? ''
  const label = cluster?.cluster_label ?? id
  const kwCount = cluster?.keyword_count ?? 0
  const oppCount = cluster?.opportunity_count ?? 0
  const topKw = cluster?.top_keywords ?? []
  const topOpp = cluster?.top_opportunities ?? []
  return (
    <div style={cardStyle} data-testid="discovery-cluster-card">
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>{label}</h3>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#666' }}>
        Keywords: {kwCount} · Opportunities: {oppCount}
      </p>
      {topKw.length > 0 && (
        <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
          <strong>Top keywords:</strong> {topKw.slice(0, 5).join(', ')}
        </div>
      )}
      {topOpp.length > 0 && (
        <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
          <strong>Top opportunities:</strong> {topOpp.slice(0, 5).join(', ')}
        </div>
      )}
    </div>
  )
}
