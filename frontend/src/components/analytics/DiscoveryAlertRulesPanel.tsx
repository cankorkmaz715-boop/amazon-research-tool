/** Steps 246–248: Discovery alert rules panel – list, create, delete. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { DiscoveryAlertRule } from '../../types/api'

const panelStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
}
const listStyle: React.CSSProperties = { listStyle: 'none', margin: 0, padding: 0 }
const rowStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid #eee' }

export interface DiscoveryAlertRulesPanelProps {
  workspaceId: number
}

export default function DiscoveryAlertRulesPanel({ workspaceId }: DiscoveryAlertRulesPanelProps) {
  const [items, setItems] = useState<DiscoveryAlertRule[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [keyword, setKeyword] = useState('')
  const [minScore, setMinScore] = useState('')

  const load = () => {
    setLoading(true)
    setError(null)
    api.getDiscoveryAlertRules(workspaceId).then((res) => {
      if (res?.data) setItems(Array.isArray(res.data) ? res.data : [])
    }).catch((e) => setError(e instanceof Error ? e.message : 'Failed')).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [workspaceId])

  const handleCreate = () => {
    const payload: { keyword?: string; min_score?: number; enabled?: boolean } = { enabled: true }
    if (keyword.trim()) payload.keyword = keyword.trim()
    const n = parseFloat(minScore)
    if (!Number.isNaN(n)) payload.min_score = n
    api.postDiscoveryAlertRule(workspaceId, payload)
      .then(() => { setKeyword(''); setMinScore(''); load() })
      .catch((e) => setError(e instanceof Error ? e.message : 'Create failed'))
  }

  const handleDelete = (id: number) => {
    api.deleteDiscoveryAlertRule(workspaceId, id).then(() => load()).catch((e) => setError(e instanceof Error ? e.message : 'Delete failed'))
  }

  if (loading && items.length === 0) return <div style={panelStyle}>Loading discovery alert rules…</div>
  return (
    <div style={panelStyle} data-testid="discovery-alert-rules-panel">
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Discovery alert rules</h3>
      {error && <p style={{ color: '#b91c1c', margin: '0 0 0.5rem', fontSize: '0.875rem' }}>{error}</p>}
      <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input placeholder="Keyword" value={keyword} onChange={(e) => setKeyword(e.target.value)} style={{ padding: '0.35rem', minWidth: 120 }} />
        <input placeholder="Min score" type="number" value={minScore} onChange={(e) => setMinScore(e.target.value)} style={{ padding: '0.35rem', width: 80 }} />
        <button type="button" onClick={handleCreate} style={{ padding: '0.35rem 0.75rem' }}>Add rule</button>
      </div>
      <ul style={listStyle}>
        {items.map((r) => (
          <li key={r.id ?? 0} style={rowStyle}>
            <span style={{ fontSize: '0.9rem' }}>
              {[r.keyword, r.market, r.category].filter(Boolean).join(' · ') || '—'}
              {r.min_score != null && ` min_score=${r.min_score}`}
              {r.enabled === false && ' (disabled)'}
            </span>
            <button type="button" onClick={() => r.id != null && handleDelete(r.id)} style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}>Delete</button>
          </li>
        ))}
      </ul>
      {items.length === 0 && !loading && <p style={{ margin: 0, fontSize: '0.875rem', color: '#666' }}>No rules.</p>}
    </div>
  )
}
