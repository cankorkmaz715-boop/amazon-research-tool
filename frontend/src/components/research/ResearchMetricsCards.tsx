/** Steps 249–250: Research performance metrics cards. */
import type { ResearchMetrics } from '../../types/api'

const cardStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  minWidth: 180,
  flex: '1 1 180px',
}
const gridStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '1rem',
}

export interface ResearchMetricsCardsProps {
  metrics: ResearchMetrics | null
}

export default function ResearchMetricsCards({ metrics }: ResearchMetricsCardsProps) {
  if (!metrics) return null

  const totalQueries = metrics.total_discovery_queries ?? 0
  const totalFound = metrics.total_opportunities_found ?? 0
  const totalConverted = metrics.total_converted_opportunities ?? 0
  const totalWatchlisted = metrics.total_watchlisted ?? 0
  const avgScore = metrics.average_score ?? '—'
  const topMarkets = metrics.top_markets ?? []
  const topCategories = metrics.top_categories ?? []
  const lastRefreshed = metrics.last_refreshed_at ?? '—'

  return (
    <div style={gridStyle} data-testid="research-metrics-cards">
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Discovery queries</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{totalQueries}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Opportunities found</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{totalFound}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Converted</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{totalConverted}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Watchlisted</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{totalWatchlisted}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Average score</div>
        <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>{avgScore}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Top markets</div>
        <div style={{ fontSize: '0.9rem' }}>{topMarkets.length ? topMarkets.join(', ') : '—'}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Top categories</div>
        <div style={{ fontSize: '0.9rem' }}>{topCategories.length ? topCategories.slice(0, 5).join(', ') : '—'}</div>
      </div>
      <div style={cardStyle}>
        <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.25rem' }}>Last refreshed</div>
        <div style={{ fontSize: '0.85rem' }}>{typeof lastRefreshed === 'string' ? lastRefreshed.slice(0, 19) : lastRefreshed}</div>
      </div>
    </div>
  )
}
