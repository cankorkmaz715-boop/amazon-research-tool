import type { OpportunityItem } from '../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function OpportunityList({ items }: { items?: OpportunityItem[] | null }) {
  const list = Array.isArray(items) ? items : []
  if (list.length === 0) {
    return (
      <section style={cardStyle} aria-label="Opportunities">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Top opportunities</h2>
        <p style={{ margin: 0, color: '#666' }}>No opportunities.</p>
      </section>
    )
  }
  return (
    <section style={cardStyle} aria-label="Opportunities">
      <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Top opportunities</h2>
      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {list.map((item, i) => (
          <li key={i} style={{ marginBottom: '0.5rem' }}>
            <strong>{item.opportunity_id ?? '—'}</strong>
            {item.priority_level && ` · ${item.priority_level}`}
            {item.opportunity_score != null && ` · score ${item.opportunity_score}`}
            {item.rationale && <div style={{ fontSize: '0.85rem', color: '#555' }}>{item.rationale}</div>}
          </li>
        ))}
      </ul>
    </section>
  )
}
