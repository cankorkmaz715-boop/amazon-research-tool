/** Steps 243–245: Compare table – compared_items, score/risk/ranking comparison. */
import type { OpportunityCompareResult } from '../../types/api'

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  marginBottom: '1rem',
  fontSize: '0.9rem',
}
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '0.5rem', borderBottom: '2px solid #e0e0e0' }
const tdStyle: React.CSSProperties = { padding: '0.5rem', borderBottom: '1px solid #eee' }
const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export default function OpportunityComparisonTable({ result }: { result: OpportunityCompareResult | null }) {
  if (!result) return null
  const items = result.compared_items ?? []
  const scoreComp = result.score_comparison ?? []
  const riskComp = result.risk_comparison ?? []
  const rankComp = result.ranking_comparison ?? []
  if (items.length === 0) return <div style={cardStyle}>No items to compare.</div>
  return (
    <div>
      <div style={cardStyle}>
        <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Compared items</h3>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>ID</th>
              <th style={thStyle}>Title</th>
              <th style={thStyle}>Score</th>
              <th style={thStyle}>Priority</th>
              <th style={thStyle}>Rank</th>
              <th style={thStyle}>Risk</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row, i) => (
              <tr key={i}>
                <td style={tdStyle}>{row.opportunity_id ?? '—'}</td>
                <td style={tdStyle}>{(row.title ?? '') || '—'}</td>
                <td style={tdStyle}>{row.score != null ? row.score : '—'}</td>
                <td style={tdStyle}>{row.priority ?? '—'}</td>
                <td style={tdStyle}>{row.ranking_position != null ? row.ranking_position : '—'}</td>
                <td style={tdStyle}>{row.risk_indicator ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scoreComp.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Score comparison</h3>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {scoreComp.map((s, i) => (
              <li key={i}>ID {s.opportunity_id}: score {s.score != null ? s.score : '—'}</li>
            ))}
          </ul>
        </div>
      )}
      {riskComp.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Risk comparison</h3>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {riskComp.map((r, i) => (
              <li key={i}>ID {r.opportunity_id}: {r.risk_indicator ?? '—'}</li>
            ))}
          </ul>
        </div>
      )}
      {rankComp.length > 0 && (
        <div style={cardStyle}>
          <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem' }}>Ranking comparison</h3>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {rankComp.map((r, i) => (
              <li key={i}>ID {r.opportunity_id}: position {r.ranking_position != null ? r.ranking_position : '—'}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
