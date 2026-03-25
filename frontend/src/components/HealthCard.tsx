import type { HealthResponse } from '../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function HealthCard({
  health,
  error,
}: {
  health: HealthResponse | null
  error: string | null
}) {
  if (error && !health) {
    return (
      <section style={cardStyle} aria-label="Backend health">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Backend health</h2>
        <p style={{ margin: 0, color: '#c00' }}>{error}</p>
      </section>
    )
  }
  if (!health) return null
  return (
    <section style={cardStyle} aria-label="Backend health">
      <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Backend health</h2>
      <p style={{ margin: 0 }}>
        Status: <strong>{health.status}</strong>
        {health.db_ok != null && ` · DB: ${health.db_ok ? 'OK' : 'Unavailable'}`}
      </p>
      <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#666' }}>
        {health.timestamp}
      </p>
    </section>
  )
}
