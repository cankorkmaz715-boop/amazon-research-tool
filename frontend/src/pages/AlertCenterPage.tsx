import { useState, useCallback, useEffect } from 'react'

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

function fmtDate(v?: string | null) {
  if (!v) return '—'
  const d = new Date(v)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function SeverityBadge({ severity }: { severity?: string }) {
  const s = (severity || 'low').toLowerCase()
  const cls =
    s === 'high'
      ? 'bg-red-500/15 text-red-400 border-red-500/30 shadow-red-500/10'
      : s === 'medium'
      ? 'bg-amber-500/15 text-amber-400 border-amber-500/30 shadow-amber-500/10'
      : 'bg-slate-500/15 text-slate-400 border-slate-500/30'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
      {s === 'high' && <span className="w-1.5 h-1.5 rounded-full bg-red-400 mr-1 animate-pulse" />}
      {s}
    </span>
  )
}

function TypeBadge({ type }: { type?: string }) {
  const label = (type || '').replace(/_/g, ' ') || '—'
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20">
      {label}
    </span>
  )
}

function StatCard({ label, value, sub, accent }: { label: string; value: number | string; sub?: string; accent?: string }) {
  return (
    <div className="glass rounded-xl p-4 flex flex-col gap-1 min-w-[100px] flex-1">
      <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</span>
      <span className={`text-2xl font-bold ${accent ?? 'text-slate-100'}`}>{value}</span>
      {sub && <span className="text-xs text-slate-600">{sub}</span>}
    </div>
  )
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
      .then(() => loadAlerts())
      .catch(() => {})
      .finally(() => setMarkingId(null))
  }

  const unread = alerts.filter((a) => !a.read_at).length
  const high = alerts.filter((a) => (a.severity || '').toLowerCase() === 'high').length
  const medium = alerts.filter((a) => (a.severity || '').toLowerCase() === 'medium').length

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-violet-500/25">
            🔔
          </div>
          <h2 className="text-xl font-bold text-slate-100">Alert Center</h2>
          {unread > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-violet-500/20 text-violet-300 border border-violet-500/30 animate-pulse-slow">
              {unread} new
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500 ml-11">
          Workspace {workspaceId} · {loaded ? `${alerts.length} total` : 'Loading…'}
        </p>
      </div>

      {/* Stat cards */}
      {loaded && (
        <div className="flex flex-wrap gap-3 mb-6 animate-slide-up">
          <StatCard label="Total" value={alerts.length} accent="text-slate-100" />
          <StatCard label="Unread" value={unread} accent="text-violet-400" />
          <StatCard label="High" value={high} accent="text-red-400" />
          <StatCard label="Medium" value={medium} accent="text-amber-400" />
          <StatCard label="Read" value={alerts.length - unread} accent="text-slate-400" />
        </div>
      )}

      {/* Filters */}
      <div className="glass rounded-xl p-4 mb-4 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Type</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all cursor-pointer"
          >
            <option value="" className="bg-slate-900">All types</option>
            <option value="high_potential" className="bg-slate-900">High potential</option>
            <option value="price_drop" className="bg-slate-900">Price drop</option>
            <option value="bsr_change" className="bg-slate-900">BSR change</option>
            <option value="new_opportunity" className="bg-slate-900">New opportunity</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Status</span>
          <select
            value={filterRead}
            onChange={(e) => setFilterRead(e.target.value)}
            className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all cursor-pointer"
          >
            <option value="" className="bg-slate-900">All status</option>
            <option value="unread" className="bg-slate-900">Unread</option>
            <option value="read" className="bg-slate-900">Read</option>
          </select>
        </div>
        <button
          type="button"
          onClick={loadAlerts}
          className="ml-auto px-4 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium transition-all duration-200 shadow-lg shadow-violet-500/20 hover:shadow-violet-500/30 hover:scale-[1.02] active:scale-[0.98]"
        >
          Apply filters
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="glass rounded-xl p-8 text-center">
          <div className="inline-block w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mb-3" />
          <p className="text-slate-500 text-sm">Loading alerts…</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass rounded-xl p-4 border-red-500/20 bg-red-500/5 text-red-400 text-sm">
          ⚠ {error}
        </div>
      )}

      {/* Empty */}
      {!loading && !error && loaded && alerts.length === 0 && (
        <div className="glass rounded-xl p-12 text-center animate-fade-in">
          <div className="text-5xl mb-4 opacity-30">🔔</div>
          <p className="text-slate-500 text-sm">No alerts found. Alerts appear when opportunities change significantly.</p>
        </div>
      )}

      {/* Alert list */}
      {!loading && !error && loaded && alerts.length > 0 && (
        <div className="glass rounded-2xl overflow-hidden glow-indigo animate-slide-up">
          {alerts.map((a, i) => {
            const isUnread = !a.read_at
            return (
              <div
                key={a.id ?? i}
                className={`
                  relative px-5 py-4 glass-hover transition-all duration-200
                  ${i < alerts.length - 1 ? 'border-b border-white/[0.05]' : ''}
                  ${isUnread ? 'bg-violet-500/[0.04]' : ''}
                `}
              >
                {isUnread && (
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-gradient-to-b from-violet-500 to-indigo-500 rounded-r" />
                )}
                <div className="flex flex-wrap items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className={`font-semibold text-sm ${isUnread ? 'text-slate-100' : 'text-slate-300'}`}>
                        {a.title || 'Alert'}
                      </span>
                      <SeverityBadge severity={a.severity} />
                      {a.alert_type && <TypeBadge type={a.alert_type} />}
                    </div>
                    {a.description && (
                      <p className="text-sm text-slate-500 mb-1.5 line-clamp-2">{a.description.slice(0, 280)}</p>
                    )}
                    <span className="text-xs text-slate-600">{fmtDate(a.recorded_at)}</span>
                  </div>
                  {isUnread && a.id && (
                    <button
                      type="button"
                      onClick={() => markRead(a.id!)}
                      disabled={markingId === a.id}
                      className="shrink-0 px-3 py-1.5 rounded-lg border border-violet-500/30 text-violet-400 text-xs font-medium hover:bg-violet-500/10 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {markingId === a.id ? '…' : 'Mark read'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
