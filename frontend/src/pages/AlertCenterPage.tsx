import { useState, useEffect, useCallback } from 'react'

interface AlertItem {
  id?: number
  alert_type?: string
  severity?: string
  title?: string
  description?: string
  recorded_at?: string
  read_at?: string | null
}

interface AlertsResponse {
  data?: AlertItem[]
  meta?: { workspace_id?: number; count?: number }
  error?: string
}

export interface AlertCenterPageProps {
  workspaceId: number
}

const S = {
  card: {
    background: '#fff',
    border: '1px solid #ddd',
    borderRadius: 6,
    marginBottom: '1rem',
    overflow: 'hidden' as const,
  },
  row: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #eee',
    fontSize: '0.875rem',
  },
  rowUnread: {
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #eee',
    fontSize: '0.875rem',
    background: '#f0f7ff',
  },
  rowHeader: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    alignItems: 'center' as const,
    gap: '0.5rem',
    marginBottom: '0.25rem',
  },
  title: { fontWeight: 600 },
  desc: { color: '#666', fontSize: '0.85rem', marginBottom: '0.2rem' },
  meta: { color: '#888', fontSize: '0.8rem' },
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
  btnMark: {
    padding: '0.2rem 0.5rem',
    fontSize: '0.8rem',
    borderRadius: 4,
    cursor: 'pointer',
    color: '#0063cc',
    background: 'transparent',
    border: '1px solid #0063cc',
  },
  loading: { color: '#888', padding: '1rem', fontSize: '0.875rem' },
  error: { color: '#c00', padding: '1rem', fontSize: '0.875rem' },
  empty: { color: '#888', fontStyle: 'italic' as const, padding: '1.5rem', textAlign: 'center' as const, fontSize: '0.875rem' },
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
}

function severityBadge(s?: string) {
  const v = (s || '').toLowerCase()
  const style: React.CSSProperties = {
    display: 'inline-block',
    padding: '0.15rem 0.45rem',
    borderRadius: 4,
    fontSize: '0.7rem',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.02em',
    ...(v === 'high'
      ? { background: '#f8d7da', color: '#721c24' }
      : v === 'medium'
      ? { background: '#fff3cd', color: '#856404' }
      : { background: '#e2e3e5', color: '#383d41' }),
  }
  return <span style={style}>{s || 'low'}</span>
}

function typeBadge(t?: string) {
  return (
    <span style={{ display: 'inline-block', padding: '0.15rem 0.45rem', borderRadius: 4, fontSize: '0.7rem', fontWeight: 500, background: '#e2e3e5', color: '#383d41', letterSpacing: '0.02em' }}>
      {t || '—'}
    </span>
  )
}

function fmtDate(v?: string | null) {
  if (!v) return '—'
  return v.slice(0, 19).replace('T', ' ')
}

export default function AlertCenterPage({ workspaceId }: AlertCenterPageProps) {
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [filterType, setFilterType] = useState('')
  const [filterRead, setFilterRead] = useState('')
  const [markingId, setMarkingId] = useState<number | null>(null)

  const loadAlerts = useCallback(() => {
    setLoading(true)
    setError(null)
    let path = `/api/workspaces/${workspaceId}/alerts?limit=100`
    if (filterType) path += `&alert_type=${encodeURIComponent(filterType)}`
    if (filterRead) path += `&read=${encodeURIComponent(filterRead)}`
    fetch(path, { headers: { Accept: 'application/json' } })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json() as Promise<AlertsResponse>
      })
      .then((body) => {
        if (body.error) throw new Error(body.error)
        setAlerts(body.data ?? [])
        setLoaded(true)
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [workspaceId, filterType, filterRead])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  function markRead(alertId: number) {
    setMarkingId(alertId)
    fetch(`/api/workspaces/${workspaceId}/alerts/${alertId}/read`, {
      method: 'PATCH',
      headers: { Accept: 'application/json' },
    })
      .then((r) => r.json())
      .then(() => loadAlerts())
      .catch(() => {})
      .finally(() => setMarkingId(null))
  }

  const unread = alerts.filter((a) => !a.read_at).length
  const total = alerts.length

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.25rem' }}>Alert Center</h2>
        <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
          Workspace {workspaceId} · {loaded ? `${total} alerts, ${unread} unread` : 'Loading…'}
        </p>
      </div>

      {loaded && (
        <div style={S.summaryBar}>
          <span style={{ fontWeight: 600 }}>Total: {total}</span>
          <span>Unread: {unread}</span>
          <span>Read: {total - unread}</span>
          {['high', 'medium', 'low'].map((sev) => {
            const cnt = alerts.filter((a) => (a.severity || 'low').toLowerCase() === sev).length
            return cnt > 0 ? <span key={sev}>{sev.charAt(0).toUpperCase() + sev.slice(1)}: {cnt}</span> : null
          })}
        </div>
      )}

      <div style={S.filters}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.875rem' }}>
          Type:
          <select style={S.select} value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="">All</option>
            <option value="high_potential">High potential</option>
            <option value="price_drop">Price drop</option>
            <option value="bsr_change">BSR change</option>
            <option value="new_opportunity">New opportunity</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.875rem' }}>
          Status:
          <select style={S.select} value={filterRead} onChange={(e) => setFilterRead(e.target.value)}>
            <option value="">All</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>
        </label>
        <button style={S.btn} type="button" onClick={loadAlerts}>Apply</button>
      </div>

      {loading && <div style={S.loading}>Loading alerts…</div>}
      {error && <div style={S.error}>Error: {error}</div>}

      {!loading && !error && loaded && (
        alerts.length === 0
          ? <div style={S.empty}>No alerts. Alerts appear here when opportunities change significantly.</div>
          : (
            <div style={S.card}>
              <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                {alerts.map((a, i) => {
                  const unreadItem = !a.read_at
                  return (
                    <li key={a.id ?? i} style={unreadItem ? S.rowUnread : { ...S.row, borderBottom: i === alerts.length - 1 ? 'none' : '1px solid #eee' }}>
                      <div style={S.rowHeader}>
                        <span style={S.title}>{a.title || 'Alert'}</span>
                        {severityBadge(a.severity)}
                        {typeBadge(a.alert_type)}
                        {unreadItem && (
                          <button
                            type="button"
                            style={{ ...S.btnMark, opacity: markingId === a.id ? 0.5 : 1 }}
                            disabled={markingId === a.id}
                            onClick={() => a.id && markRead(a.id)}
                          >
                            {markingId === a.id ? '…' : 'Mark read'}
                          </button>
                        )}
                      </div>
                      {a.description && <div style={S.desc}>{a.description.slice(0, 300)}</div>}
                      <div style={S.meta}>{fmtDate(a.recorded_at)}</div>
                    </li>
                  )
                })}
              </ul>
            </div>
          )
      )}
    </div>
  )
}
