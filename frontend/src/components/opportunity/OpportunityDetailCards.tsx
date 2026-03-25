/**
 * Pipeline: Opportunity detail cards – display id, title, score, priority, rationale, action, risk, market, category, history.
 */
import type { OpportunityDetail } from '../../types/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

const labelStyle: React.CSSProperties = { fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }
const valueStyle: React.CSSProperties = { fontSize: '1rem' }

export default function OpportunityDetailCards({ detail }: { detail: OpportunityDetail | null }) {
  if (!detail) return null
  const history = Array.isArray(detail.history) ? detail.history : []
  return (
    <div>
      <div style={cardStyle}>
        <h2 style={{ margin: '0 0 0.75rem', fontSize: '1.1rem' }}>{detail.title ?? 'Opportunity'}</h2>
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {detail.score != null && (
            <div>
              <div style={labelStyle}>Score</div>
              <div style={valueStyle}>{detail.score}</div>
            </div>
          )}
          {detail.priority && (
            <div>
              <div style={labelStyle}>Priority</div>
              <div style={valueStyle}>{detail.priority}</div>
            </div>
          )}
          {detail.ranking_position != null && (
            <div>
              <div style={labelStyle}>Ranking position</div>
              <div style={valueStyle}>{detail.ranking_position}</div>
            </div>
          )}
          {detail.rationale_summary && (
            <div>
              <div style={labelStyle}>Rationale</div>
              <div style={valueStyle}>{detail.rationale_summary}</div>
            </div>
          )}
          {detail.recommended_action && (
            <div>
              <div style={labelStyle}>Recommended action</div>
              <div style={valueStyle}>{detail.recommended_action}</div>
            </div>
          )}
          {detail.risk_indicator && (
            <div>
              <div style={labelStyle}>Risk</div>
              <div style={valueStyle}>{detail.risk_indicator}</div>
            </div>
          )}
          {detail.market && (
            <div>
              <div style={labelStyle}>Market</div>
              <div style={valueStyle}>{detail.market}</div>
            </div>
          )}
          {detail.category && (
            <div>
              <div style={labelStyle}>Category</div>
              <div style={valueStyle}>{detail.category}</div>
            </div>
          )}
        </div>
      </div>
      {history.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>History</h3>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.9rem' }}>
            {history.slice(0, 10).map((h: unknown, i: number) => (
              <li key={i}>{typeof h === 'object' && h !== null && 'at' in (h as object) ? String((h as { at?: string }).at) : String(h)}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
