import type { PortfolioSummary } from '../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function PortfolioSummaryCard({ data }: { data?: PortfolioSummary | Record<string, unknown> | null }) {
  if (!data || typeof data !== 'object') {
    return (
      <section style={cardStyle} aria-label="Portfolio summary">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Portfolio summary</h2>
        <p style={{ margin: 0, color: '#666' }}>No portfolio summary.</p>
      </section>
    )
  }
  const total = (data as PortfolioSummary).total ?? 0
  const byStatus = (data as PortfolioSummary).by_status ?? {}
  const byType = (data as PortfolioSummary).by_type ?? {}
  return (
    <section style={cardStyle} aria-label="Portfolio summary">
      <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Portfolio summary</h2>
      <p style={{ margin: 0 }}>Total: <strong>{total}</strong></p>
      {Object.keys(byStatus).length > 0 && (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
          By status: {Object.entries(byStatus).map(([k, v]) => `${k}: ${v}`).join(', ')}
        </p>
      )}
      {Object.keys(byType).length > 0 && (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
          By type: {Object.entries(byType).map(([k, v]) => `${k}: ${v}`).join(', ')}
        </p>
      )}
    </section>
  )
}
