/** Steps 243–245: Opportunity comparison page. Max 5 IDs. */
import { useState } from 'react'
import { api } from '../../lib/api'
import type { OpportunityCompareResult } from '../../types/api'
import OpportunityComparisonTable from '../../components/opportunity/OpportunityComparisonTable'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
}

export interface OpportunityComparisonPageProps {
  workspaceId: number
}

export default function OpportunityComparisonPage({ workspaceId }: OpportunityComparisonPageProps) {
  const [idsInput, setIdsInput] = useState('1,2,3')
  const [result, setResult] = useState<OpportunityCompareResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCompare = () => {
    const ids = idsInput
      .split(/[\s,]+/)
      .map((s) => parseInt(s.trim(), 10))
      .filter((n) => !Number.isNaN(n) && n > 0)
      .slice(0, 5)
    setLoading(true)
    setError(null)
    setResult(null)
    api
      .postOpportunitiesCompare(workspaceId, ids)
      .then((res) => { if (res?.data) setResult(res.data) })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed'))
      .finally(() => setLoading(false))
  }

  return (
    <div>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Compare opportunities (max 5)</h2>
      <div style={cardStyle}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
          Opportunity IDs (comma-separated):
          <input
            type="text"
            value={idsInput}
            onChange={(e) => setIdsInput(e.target.value)}
            style={{ marginLeft: '0.5rem', padding: '0.35rem', minWidth: 200 }}
          />
        </label>
        <button type="button" onClick={handleCompare} disabled={loading} style={{ padding: '0.5rem 1rem' }}>
          {loading ? 'Comparing…' : 'Compare'}
        </button>
        {error && <span style={{ marginLeft: '0.5rem', color: '#b91c1c' }}>{error}</span>}
      </div>
      {result && <OpportunityComparisonTable result={result} />}
    </div>
  )
}
