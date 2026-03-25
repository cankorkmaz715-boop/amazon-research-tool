/** Steps 243–245: Single category explorer card. */
import type { CategoryExplorerItem } from '../../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function CategoryExplorerCard({ item }: { item: CategoryExplorerItem }) {
  const category = item?.category ?? '—'
  const oppCount = item?.opportunity_count ?? 0
  const kwCount = item?.keyword_count ?? 0
  const topOpp = item?.top_opportunities ?? []
  const topKw = item?.top_keywords ?? []
  return (
    <div style={cardStyle} data-testid="category-explorer-card">
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>{category}</h3>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#666' }}>
        Opportunities: {oppCount} · Keywords: {kwCount}
      </p>
      {topOpp.length > 0 && (
        <div style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>
          <strong>Top opportunities:</strong> {topOpp.slice(0, 5).join(', ')}
        </div>
      )}
      {topKw.length > 0 && (
        <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
          <strong>Top keywords:</strong> {topKw.slice(0, 5).join(', ')}
        </div>
      )}
    </div>
  )
}
