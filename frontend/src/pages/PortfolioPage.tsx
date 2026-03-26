import { useState, useEffect, useCallback, useRef } from 'react'

interface PortfolioItem {
  id?: number
  item_type?: string
  item_key?: string
  item_label?: string
  source_type?: string
  status?: string
  created_at?: string
  updated_at?: string
}

interface PortfolioSummary {
  total?: number
  by_status?: Record<string, number>
  by_type?: Record<string, number>
}

export interface PortfolioPageProps {
  workspaceId: number
}

const S = {
  summaryBar: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    gap: '1rem',
    padding: '0.75rem 1rem',
    background: '#fff',
    border: '1px solid #ddd',
    borderRadius: 6,
    fontSize: '0.875rem',
    marginBottom: '1rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  filters: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    gap: '0.75rem',
    alignItems: 'center' as const,
    marginBottom: '1rem',
  },
  select: { padding: '0.25rem 0.5rem', fontSize: '0.875rem' },
  btn: {
    padding: '0.25rem 0.75rem',
    fontSize: '0.875rem',
    cursor: 'pointer',
    borderRadius: 4,
    border: '1px solid #ccc',
    background: '#f8f8f8',
  },
  exportBtn: {
    padding: '0.25rem 0.65rem',
    fontSize: '0.85rem',
    cursor: 'pointer',
    borderRadius: 4,
    border: '1px solid #ccc',
    background: '#fff',
  },
  tableWrap: {
    border: '1px solid #ddd',
    borderRadius: 6,
    overflow: 'auto' as const,
    background: '#fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '0.875rem' },
  th: { padding: '0.5rem 0.75rem', textAlign: 'left' as const, borderBottom: '1px solid #ddd', background: '#fafafa', fontWeight: 600, whiteSpace: 'nowrap' as const },
  td: { padding: '0.5rem 0.75rem', borderBottom: '1px solid #eee', verticalAlign: 'middle' as const },
  loading: { color: '#888', padding: '1rem', fontSize: '0.875rem' },
  error: { color: '#c00', padding: '1rem', fontSize: '0.875rem' },
  empty: { color: '#888', fontStyle: 'italic' as const, padding: '1.5rem', textAlign: 'center' as const, fontSize: '0.875rem' },
  btnArchive: {
    padding: '0.2rem 0.5rem',
    fontSize: '0.8rem',
    borderRadius: 4,
    cursor: 'pointer',
    color: '#856404',
    background: '#fff3cd',
    border: '1px solid #ffc107',
  },
  exportMenu: {
    position: 'absolute' as const,
    top: '100%',
    left: 0,
    minWidth: '10rem',
    background: '#fff',
    border: '1px solid #ddd',
    borderRadius: 4,
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    zIndex: 20,
    padding: '0.25rem 0',
    marginTop: '0.25rem',
  },
  exportMenuItem: {
    display: 'block' as const,
    padding: '0.4rem 0.75rem',
    fontSize: '0.875rem',
    color: '#333',
    textDecoration: 'none' as const,
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    width: '100%',
    textAlign: 'left' as const,
  },
}

function statusBadge(s?: string) {
  const v = (s || 'active').toLowerCase()
  const style: React.CSSProperties = {
    display: 'inline-block',
    padding: '0.15rem 0.45rem',
    borderRadius: 4,
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.02em',
    ...(v === 'archived'
      ? { background: '#e2e3e5', color: '#383d41' }
      : { background: '#d4edda', color: '#155724' }),
  }
  return <span style={style}>{v}</span>
}

function fmtDate(v?: string | null) {
  if (!v) return '—'
  return v.slice(0, 19).replace('T', ' ')
}

const EXPORT_OPTIONS = [
  { label: 'Dashboard (JSON)', type: 'dashboard', format: 'json' },
  { label: 'Opportunities (CSV)', type: 'opportunities', format: 'csv' },
  { label: 'Portfolio (CSV)', type: 'portfolio', format: 'csv' },
  { label: 'Alerts (CSV)', type: 'alerts', format: 'csv' },
]

export default function PortfolioPage({ workspaceId }: PortfolioPageProps) {
  const [items, setItems] = useState<PortfolioItem[]>([])
  const [summary, setSummary] = useState<PortfolioSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')
  const [archivingId, setArchivingId] = useState<number | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const exportRef = useRef<HTMLDivElement>(null)

  const loadPortfolio = useCallback(() => {
    setLoading(true)
    setError(null)
    let listPath = `/api/workspaces/${workspaceId}/portfolio?limit=500`
    if (filterStatus) listPath += `&status=${encodeURIComponent(filterStatus)}`
    if (filterType) listPath += `&item_type=${encodeURIComponent(filterType)}`
    const summaryPath = `/api/workspaces/${workspaceId}/portfolio/summary`
    Promise.all([
      fetch(summaryPath, { headers: { Accept: 'application/json' } }).then((r) => r.json()),
      fetch(listPath, { headers: { Accept: 'application/json' } }).then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json()
      }),
    ])
      .then(([sumBody, listBody]) => {
        if (listBody.error) throw new Error(listBody.error)
        setSummary(sumBody?.data ?? sumBody ?? null)
        setItems(listBody?.data ?? [])
        setLoaded(true)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [workspaceId, filterStatus, filterType])

  useEffect(() => { loadPortfolio() }, [loadPortfolio])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function archiveItem(itemId: number) {
    setArchivingId(itemId)
    fetch(`/api/workspaces/${workspaceId}/portfolio/${itemId}/archive`, {
      method: 'PATCH',
      headers: { Accept: 'application/json' },
    })
      .then((r) => r.json())
      .then((body) => {
        if (body?.data?.archived || body?.data?.status === 'archived') loadPortfolio()
        else setError(body?.error || 'Archive failed.')
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setArchivingId(null))
  }

  function doExport(type: string, format: string) {
    setExportOpen(false)
    setExportError(null)
    const path = `/api/workspaces/${workspaceId}/export/${encodeURIComponent(type)}?format=${encodeURIComponent(format)}`
    fetch(path, { headers: { Accept: 'application/json' } })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.text()
      })
      .then((text) => {
        const ext = format === 'csv' ? 'csv' : 'json'
        const filename = `workspace-${workspaceId}-${type}.${ext}`
        const blob = new Blob([text], { type: format === 'csv' ? 'text/csv' : 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = filename
        a.click()
        URL.revokeObjectURL(a.href)
      })
      .catch((e) => setExportError(e instanceof Error ? e.message : 'Export failed.'))
  }

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.25rem' }}>Portfolio</h2>
          <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
            Workspace {workspaceId} · {loaded ? `${items.length} items` : 'Loading…'}
          </p>
        </div>
        <div style={{ position: 'relative' }} ref={exportRef}>
          <button style={S.exportBtn} type="button" onClick={() => setExportOpen((v) => !v)}>
            Export ▾
          </button>
          {exportOpen && (
            <div style={S.exportMenu}>
              {EXPORT_OPTIONS.map((opt) => (
                <button
                  key={opt.type}
                  style={S.exportMenuItem}
                  type="button"
                  onClick={() => doExport(opt.type, opt.format)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {exportError && <div style={{ ...S.error, marginBottom: '0.75rem' }}>Export error: {exportError}</div>}

      {loaded && summary && (
        <div style={S.summaryBar}>
          <span style={{ fontWeight: 600 }}>Total: {summary.total ?? items.length}</span>
          <span>Active: {summary.by_status?.active ?? 0}</span>
          <span>Archived: {summary.by_status?.archived ?? 0}</span>
          {summary.by_type && Object.entries(summary.by_type).map(([t, cnt]) => (
            <span key={t}>{t}: {cnt}</span>
          ))}
        </div>
      )}

      <div style={S.filters}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.875rem' }}>
          Status:
          <select style={S.select} value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="archived">Archived</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.875rem' }}>
          Type:
          <select style={S.select} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All</option>
            <option value="opportunity">Opportunity</option>
            <option value="asin">ASIN</option>
            <option value="niche">Niche</option>
            <option value="category">Category</option>
            <option value="market">Market</option>
            <option value="keyword">Keyword</option>
          </select>
        </label>
        <button style={S.btn} type="button" onClick={loadPortfolio}>Apply</button>
      </div>

      {loading && <div style={S.loading}>Loading portfolio…</div>}
      {error && <div style={S.error}>Error: {error}</div>}

      {!loading && !error && loaded && (
        items.length === 0
          ? <div style={S.empty}>No portfolio items. Watch an opportunity to add it here.</div>
          : (
            <div style={S.tableWrap}>
              <table style={S.table}>
                <thead>
                  <tr>
                    <th style={S.th}>ID</th>
                    <th style={S.th}>Type</th>
                    <th style={S.th}>Key</th>
                    <th style={S.th}>Label</th>
                    <th style={S.th}>Source</th>
                    <th style={S.th}>Status</th>
                    <th style={S.th}>Updated</th>
                    <th style={S.th}></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={it.id ?? i}>
                      <td style={S.td}>{it.id ?? '—'}</td>
                      <td style={S.td}>{it.item_type || '—'}</td>
                      <td style={{ ...S.td, fontFamily: 'monospace', fontSize: '0.8rem' }}>{it.item_key || '—'}</td>
                      <td style={S.td}>{it.item_label || '—'}</td>
                      <td style={S.td}>{it.source_type || '—'}</td>
                      <td style={S.td}>{statusBadge(it.status)}</td>
                      <td style={S.td}>{fmtDate(it.updated_at || it.created_at)}</td>
                      <td style={S.td}>
                        {(it.status || 'active').toLowerCase() === 'active' && it.id ? (
                          <button
                            type="button"
                            style={{ ...S.btnArchive, opacity: archivingId === it.id ? 0.6 : 1 }}
                            disabled={archivingId === it.id}
                            onClick={() => archiveItem(it.id!)}
                          >
                            {archivingId === it.id ? 'Archiving…' : 'Archive'}
                          </button>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
      )}
    </div>
  )
}
