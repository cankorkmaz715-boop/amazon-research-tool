/**
 * Step 239/240: Single result card for keyword or market item.
 * Step 240: "Convert to Opportunity" action.
 */
import { useState } from 'react'
import type { DiscoveryKeywordItem, DiscoveryMarketItem } from '../../types/api'
import { api } from '../../lib/api'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 6,
  padding: '0.75rem 1rem',
  marginBottom: '0.5rem',
}

const buttonStyle: React.CSSProperties = {
  marginTop: '0.5rem',
  padding: '0.35rem 0.6rem',
  fontSize: '0.8rem',
  cursor: 'pointer',
}

export function KeywordResultCard({ item, workspaceId }: { item: DiscoveryKeywordItem; workspaceId?: number }) {
  const [converting, setConverting] = useState(false)
  const [convertStatus, setConvertStatus] = useState<string | null>(null)
  const keyword = item?.keyword ?? '—'
  const market = item?.market ?? ''
  const count = item?.result_count ?? item?.opportunity_count ?? 0
  const refs = item?.top_opportunity_refs ?? []
  const last = item?.last_observed_at ?? null
  const wid = workspaceId ?? 1

  const handleConvert = async () => {
    if (!String(keyword).trim()) return
    setConverting(true)
    setConvertStatus(null)
    try {
      const res = await api.postOpportunityFromDiscovery(wid, {
        keyword: String(keyword).trim(),
        market: market || undefined,
      })
      const status = res?.data?.status ?? 'created'
      setConvertStatus(res?.data?.message ?? status)
    } catch (e) {
      setConvertStatus(e instanceof Error ? e.message : 'Failed')
    } finally {
      setConverting(false)
    }
  }

  return (
    <div style={cardStyle} data-testid="discovery-keyword-card">
      <div style={{ fontWeight: 600 }}>{String(keyword)}</div>
      {market && <span style={{ fontSize: '0.85rem', color: '#666' }}>Market: {market}</span>}
      {(count > 0 || refs.length > 0) && (
        <div style={{ fontSize: '0.85rem', color: '#555', marginTop: '0.25rem' }}>
          {count > 0 && `Results: ${count}`}
          {refs.length > 0 && refs.slice(0, 3).map((r, i) => (
            <span key={i} style={{ marginLeft: '0.5rem' }}>{r}</span>
          ))}
        </div>
      )}
      {last && <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.25rem' }}>Last: {last}</div>}
      <div style={{ marginTop: '0.5rem' }}>
        <button type="button" onClick={handleConvert} disabled={converting} style={buttonStyle}>
          {converting ? 'Converting…' : 'Convert to Opportunity'}
        </button>
        {convertStatus && <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#059669' }}>{convertStatus}</span>}
      </div>
    </div>
  )
}

export function MarketResultCard({ item, workspaceId }: { item: DiscoveryMarketItem; workspaceId?: number }) {
  const [converting, setConverting] = useState(false)
  const [convertStatus, setConvertStatus] = useState<string | null>(null)
  const marketKey = item?.market_key ?? '—'
  const count = item?.discovery_count ?? 0
  const categories = item?.top_categories ?? []
  const opportunities = item?.top_opportunities ?? []
  const last = item?.last_observed_at ?? null
  const wid = workspaceId ?? 1

  const handleConvert = async () => {
    const mk = String(marketKey).trim()
    if (!mk) return
    setConverting(true)
    setConvertStatus(null)
    try {
      const res = await api.postOpportunityFromDiscovery(wid, {
        discovery_id: `market:${mk}`,
        market: mk,
      })
      setConvertStatus(res?.data?.message ?? res?.data?.status ?? 'created')
    } catch (e) {
      setConvertStatus(e instanceof Error ? e.message : 'Failed')
    } finally {
      setConverting(false)
    }
  }

  return (
    <div style={cardStyle} data-testid="discovery-market-card">
      <div style={{ fontWeight: 600 }}>Market: {String(marketKey)}</div>
      {count > 0 && <span style={{ fontSize: '0.85rem', color: '#666' }}>Discovery count: {count}</span>}
      {(categories.length > 0 || opportunities.length > 0) && (
        <div style={{ fontSize: '0.85rem', color: '#555', marginTop: '0.25rem' }}>
          {categories.length > 0 && <div>Categories: {categories.slice(0, 3).join(', ')}</div>}
          {opportunities.length > 0 && <div>Opportunities: {opportunities.slice(0, 3).join(', ')}</div>}
        </div>
      )}
      {last && <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '0.25rem' }}>Last: {last}</div>}
      <div style={{ marginTop: '0.5rem' }}>
        <button type="button" onClick={handleConvert} disabled={converting} style={buttonStyle}>
          {converting ? 'Converting…' : 'Convert to Opportunity'}
        </button>
        {convertStatus && <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: '#059669' }}>{convertStatus}</span>}
      </div>
    </div>
  )
}
