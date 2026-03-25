import type { DashboardOverview } from '../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function OverviewCard({ data }: { data?: DashboardOverview | null }) {
  if (!data) {
    return (
      <section style={cardStyle} aria-label="Overview">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Overview</h2>
        <p style={{ margin: 0, color: '#666' }}>No overview data.</p>
      </section>
    )
  }
  const totalOpps = data.total_opportunities ?? 0
  const highPriority = data.high_priority_opportunities ?? 0
  const portfolioItems = data.total_portfolio_items ?? 0
  const highRisk = data.high_risk_item_count ?? 0
  return (
    <section style={cardStyle} aria-label="Overview">
      <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Overview</h2>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
        <span>Opportunities: <strong>{totalOpps}</strong></span>
        <span>High priority: <strong>{highPriority}</strong></span>
        <span>Portfolio items: <strong>{portfolioItems}</strong></span>
        <span>High risk: <strong>{highRisk}</strong></span>
      </div>
    </section>
  )
}
