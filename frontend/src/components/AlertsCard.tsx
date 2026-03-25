import type { AlertItem } from '../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function AlertsCard({ items }: { items?: AlertItem[] | null }) {
  const list = Array.isArray(items) ? items : []
  if (list.length === 0) {
    return (
      <section style={cardStyle} aria-label="Alerts">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Alerts</h2>
        <p style={{ margin: 0, color: '#666' }}>No alerts.</p>
      </section>
    )
  }
  return (
    <section style={cardStyle} aria-label="Alerts">
      <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Alerts</h2>
      <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
        {list.map((a, i) => (
          <li key={a.id ?? i} style={{ marginBottom: '0.5rem' }}>
            <strong>{a.title ?? 'Alert'}</strong>
            {a.severity && ` · ${a.severity}`}
            {a.recorded_at && <span style={{ fontSize: '0.8rem', color: '#666' }}> · {a.recorded_at.slice(0, 19)}</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}
