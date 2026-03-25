const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function StrategySummaryCard({ data }: { data?: Record<string, unknown> | null }) {
  if (!data || typeof data !== 'object') {
    return (
      <section style={cardStyle} aria-label="Strategy summary">
        <h2 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Strategy summary</h2>
        <p style={{ margin: 0, color: '#666' }}>No strategy summary.</p>
      </section>
    )
  }
  const generatedAt = data.generated_at as string | undefined
  const actNow = Array.isArray(data.prioritized_opportunities) ? data.prioritized_opportunities.length : 0
  const monitor = Array.isArray(data.monitor_opportunities) ? data.monitor_opportunities.length : 0
  return (
    <section style={cardStyle} aria-label="Strategy summary">
      <h2 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Strategy summary</h2>
      <p style={{ margin: 0 }}>Prioritized (act now): <strong>{actNow}</strong></p>
      <p style={{ margin: '0.35rem 0 0' }}>Monitor: <strong>{monitor}</strong></p>
      {generatedAt && (
        <p style={{ margin: '0.35rem 0 0', fontSize: '0.8rem', color: '#666' }}>{generatedAt.slice(0, 19)}</p>
      )}
    </section>
  )
}
