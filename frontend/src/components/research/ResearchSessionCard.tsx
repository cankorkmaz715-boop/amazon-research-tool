/** Steps 249–250: Single research session card. */
import type { ResearchSession } from '../../types/api'

const cardStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export interface ResearchSessionCardProps {
  session: ResearchSession
}

export default function ResearchSessionCard({ session }: ResearchSessionCardProps) {
  const label = session?.label ?? '—'
  const created = session?.created_at ?? '—'
  const searches = session?.attached_searches ?? []
  const opportunities = session?.attached_opportunities ?? []
  const notes = session?.notes_summary ?? ''

  return (
    <div style={cardStyle} data-testid="research-session-card">
      <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>{label}</h3>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.875rem', color: '#666' }}>
        Created: {created}
      </p>
      <p style={{ margin: '0 0 0.25rem', fontSize: '0.85rem' }}>
        Attached searches: {Array.isArray(searches) ? searches.length : 0}
      </p>
      <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem' }}>
        Attached opportunities: {Array.isArray(opportunities) ? opportunities.length : 0}
      </p>
      {notes && (
        <p style={{ margin: 0, fontSize: '0.85rem', color: '#555' }}>
          Notes: {notes}
        </p>
      )}
    </div>
  )
}
