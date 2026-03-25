/** Steps 246–248: Saved searches panel – list, create, delete. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { SavedSearch } from '../../types/api'

const panelStyle: React.CSSProperties = {
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem',
  marginBottom: '1rem',
  background: '#fff',
}
const listStyle: React.CSSProperties = { listStyle: 'none', margin: 0, padding: 0 }
const rowStyle: React.CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid #eee' }

export interface SavedSearchPanelProps {
  workspaceId: number
}

export default function SavedSearchPanel({ workspaceId }: SavedSearchPanelProps) {
  const [items, setItems] = useState<SavedSearch[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [label, setLabel] = useState('')
  const [query, setQuery] = useState('')

  const load = () => {
    setLoading(true)
    setError(null)
    api.getSavedSearches(workspaceId).then((res) => {
      if (res?.data) setItems(Array.isArray(res.data) ? res.data : [])
    }).catch((e) => setError(e instanceof Error ? e.message : 'Failed')).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [workspaceId])

  const handleCreate = () => {
    if (!label.trim()) return
    api.postSavedSearch(workspaceId, { label: label.trim(), query: query.trim() || undefined })
      .then(() => { setLabel(''); setQuery(''); load() })
      .catch((e) => setError(e instanceof Error ? e.message : 'Create failed'))
  }

  const handleDelete = (id: number) => {
    api.deleteSavedSearch(workspaceId, id).then(() => load()).catch((e) => setError(e instanceof Error ? e.message : 'Delete failed'))
  }

  if (loading && items.length === 0) return <div style={panelStyle}>Loading saved searches…</div>
  return (
    <div style={panelStyle} data-testid="saved-search-panel">
      <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem' }}>Saved searches</h3>
      {error && <p style={{ color: '#b91c1c', margin: '0 0 0.5rem', fontSize: '0.875rem' }}>{error}</p>}
      <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <input placeholder="Label" value={label} onChange={(e) => setLabel(e.target.value)} style={{ padding: '0.35rem', minWidth: 120 }} />
        <input placeholder="Query" value={query} onChange={(e) => setQuery(e.target.value)} style={{ padding: '0.35rem', minWidth: 160 }} />
        <button type="button" onClick={handleCreate} style={{ padding: '0.35rem 0.75rem' }}>Save</button>
      </div>
      <ul style={listStyle}>
        {items.map((s) => (
          <li key={s.id ?? 0} style={rowStyle}>
            <span style={{ fontSize: '0.9rem' }}>{s.label ?? '—'} {s.query && `(${s.query})`}</span>
            <button type="button" onClick={() => s.id != null && handleDelete(s.id)} style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}>Delete</button>
          </li>
        ))}
      </ul>
      {items.length === 0 && !loading && <p style={{ margin: 0, fontSize: '0.875rem', color: '#666' }}>No saved searches.</p>}
    </div>
  )
}
