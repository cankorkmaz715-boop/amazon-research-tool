/**
 * Pipeline: Opportunity detail page – fetch and show detail, watch button.
 */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { OpportunityDetail } from '../../types/api'
import OpportunityDetailCards from '../../components/opportunity/OpportunityDetailCards'
import OpportunityWatchButton from '../../components/opportunity/OpportunityWatchButton'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
}

export interface OpportunityDetailPageProps {
  workspaceId: number
  opportunityId: number
}

export default function OpportunityDetailPage({ workspaceId, opportunityId }: OpportunityDetailPageProps) {
  const [detail, setDetail] = useState<OpportunityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .getOpportunityDetail(workspaceId, opportunityId)
      .then((res) => {
        if (!cancelled && res?.data) setDetail(res.data)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [workspaceId, opportunityId])

  if (loading) return <div style={cardStyle}>Loading opportunity…</div>
  if (error) return <div style={{ ...cardStyle, color: '#b91c1c' }}>{error}</div>
  if (!detail) return <div style={cardStyle}>Opportunity not found.</div>

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
        <OpportunityWatchButton workspaceId={workspaceId} opportunityId={opportunityId} />
      </div>
      <OpportunityDetailCards detail={detail} />
    </div>
  )
}
