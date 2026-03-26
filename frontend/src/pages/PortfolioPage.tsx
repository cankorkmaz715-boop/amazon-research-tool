import { useState, useCallback, useEffect, useRef } from 'react'

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

function fmtDate(v?: string | null) {
  if (!v) return '—'
  const d = new Date(v)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function StatusBadge({ status }: { status?: string }) {
  const s = (status || 'active').toLowerCase()
  return s === 'archived' ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-slate-500/15 text-slate-500 border border-slate-500/25">
      Archived
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
      Active
    </span>
  )
}

function TypeBadge({ type }: { type?: string }) {
  const colors: Record<string, string> = {
    opportunity: 'bg-violet-500/15 text-violet-400 border-violet-500/25',
    asin: 'bg-blue-500/15 text-blue-400 border-blue-500/25',
    niche: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/25',
    category: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/25',
    market: 'bg-teal-500/15 text-teal-400 border-teal-500/25',
    keyword: 'bg-fuchsia-500/15 text-fuchsia-400 border-fuchsia-500/25',
  }
  const cls = colors[(type || '').toLowerCase()] ?? 'bg-slate-500/15 text-slate-400 border-slate-500/25'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border ${cls}`}>
      {type || '—'}
    </span>
  )
}

function StatCard({ label, value, accent }: { label: string; value: number | string; accent?: string }) {
  return (
    <div className="glass rounded-xl p-4 flex flex-col gap-1 flex-1 min-w-[90px]">
      <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">{label}</span>
      <span className={`text-2xl font-bold ${accent ?? 'text-slate-100'}`}>{value}</span>
    </div>
  )
}

const EXPORT_OPTIONS = [
  { label: 'Dashboard JSON', type: 'dashboard', format: 'json', icon: '📊' },
  { label: 'Opportunities CSV', type: 'opportunities', format: 'csv', icon: '💡' },
  { label: 'Portfolio CSV', type: 'portfolio', format: 'csv', icon: '📁' },
  { label: 'Alerts CSV', type: 'alerts', format: 'csv', icon: '🔔' },
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
  const [exportMsg, setExportMsg] = useState<string | null>(null)
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
    function handler(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) setExportOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function archiveItem(itemId: number) {
    setArchivingId(itemId)
    fetch(`/api/workspaces/${workspaceId}/portfolio/${itemId}/archive`, {
      method: 'PATCH', headers: { Accept: 'application/json' },
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
    setExportMsg(null)
    fetch(`/api/workspaces/${workspaceId}/export/${encodeURIComponent(type)}?format=${encodeURIComponent(format)}`, {
      headers: { Accept: 'application/json' },
    })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.text()
      })
      .then((text) => {
        const ext = format === 'csv' ? 'csv' : 'json'
        const blob = new Blob([text], { type: format === 'csv' ? 'text/csv' : 'application/json' })
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = `workspace-${workspaceId}-${type}.${ext}`
        a.click()
        URL.revokeObjectURL(a.href)
        setExportMsg(`${type}.${ext} downloaded`)
        setTimeout(() => setExportMsg(null), 3000)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Export failed.'))
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/25">
              📁
            </div>
            <h2 className="text-xl font-bold text-slate-100">Portfolio</h2>
          </div>
          <p className="text-sm text-slate-500 ml-11">
            Workspace {workspaceId} · {loaded ? `${items.length} items tracked` : 'Loading…'}
          </p>
        </div>

        {/* Export button */}
        <div className="relative" ref={exportRef}>
          <button
            type="button"
            onClick={() => setExportOpen((v) => !v)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg glass border border-white/10 hover:border-violet-500/30 text-slate-300 hover:text-slate-100 text-sm font-medium transition-all duration-200 hover:bg-white/5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export
            <svg className={`w-3 h-3 transition-transform duration-200 ${exportOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {exportOpen && (
            <div className="absolute right-0 top-full mt-2 w-48 glass rounded-xl border border-white/10 shadow-2xl shadow-black/50 z-30 overflow-hidden animate-slide-up">
              {EXPORT_OPTIONS.map((opt) => (
                <button
                  key={opt.type}
                  type="button"
                  onClick={() => doExport(opt.type, opt.format)}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-slate-300 hover:text-slate-100 hover:bg-white/5 transition-all duration-150"
                >
                  <span className="text-base">{opt.icon}</span>
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {exportMsg && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm animate-fade-in">
          ✓ {exportMsg}
        </div>
      )}

      {/* Stats */}
      {loaded && summary && (
        <div className="flex flex-wrap gap-3 mb-6 animate-slide-up">
          <StatCard label="Total" value={summary.total ?? items.length} />
          <StatCard label="Active" value={summary.by_status?.active ?? 0} accent="text-emerald-400" />
          <StatCard label="Archived" value={summary.by_status?.archived ?? 0} accent="text-slate-500" />
          {summary.by_type && Object.entries(summary.by_type).slice(0, 4).map(([t, cnt]) => (
            <StatCard key={t} label={t} value={cnt} />
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="glass rounded-xl p-4 mb-4 flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Status</span>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all cursor-pointer"
          >
            <option value="" className="bg-slate-900">All status</option>
            <option value="active" className="bg-slate-900">Active</option>
            <option value="archived" className="bg-slate-900">Archived</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">Type</span>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all cursor-pointer"
          >
            <option value="" className="bg-slate-900">All types</option>
            <option value="opportunity" className="bg-slate-900">Opportunity</option>
            <option value="asin" className="bg-slate-900">ASIN</option>
            <option value="niche" className="bg-slate-900">Niche</option>
            <option value="category" className="bg-slate-900">Category</option>
            <option value="market" className="bg-slate-900">Market</option>
            <option value="keyword" className="bg-slate-900">Keyword</option>
          </select>
        </div>
        <button
          type="button"
          onClick={loadPortfolio}
          className="ml-auto px-4 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-sm font-medium transition-all duration-200 shadow-lg shadow-violet-500/20 hover:scale-[1.02] active:scale-[0.98]"
        >
          Apply
        </button>
      </div>

      {loading && (
        <div className="glass rounded-xl p-8 text-center">
          <div className="inline-block w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mb-3" />
          <p className="text-slate-500 text-sm">Loading portfolio…</p>
        </div>
      )}
      {error && <div className="glass rounded-xl p-4 bg-red-500/5 border-red-500/20 text-red-400 text-sm mb-4">⚠ {error}</div>}

      {!loading && !error && loaded && items.length === 0 && (
        <div className="glass rounded-xl p-12 text-center animate-fade-in">
          <div className="text-5xl mb-4 opacity-30">📁</div>
          <p className="text-slate-500 text-sm">No portfolio items yet. Watch an opportunity to add it here.</p>
        </div>
      )}

      {/* Table */}
      {!loading && !error && loaded && items.length > 0 && (
        <div className="glass rounded-2xl overflow-hidden glow-indigo animate-slide-up">
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.07]">
                  {['ID', 'Type', 'Key', 'Label', 'Source', 'Status', 'Updated', ''].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider whitespace-nowrap bg-white/[0.02]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((it, i) => (
                  <tr
                    key={it.id ?? i}
                    className={`border-b border-white/[0.04] transition-colors duration-150 hover:bg-white/[0.03] ${i === items.length - 1 ? 'border-b-0' : ''}`}
                  >
                    <td className="px-4 py-3 text-xs text-slate-500 font-mono">{it.id ?? '—'}</td>
                    <td className="px-4 py-3"><TypeBadge type={it.item_type} /></td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-400 max-w-[140px] truncate">{it.item_key || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-300 max-w-[180px] truncate">{it.item_label || '—'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{it.source_type || '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={it.status} /></td>
                    <td className="px-4 py-3 text-xs text-slate-500 whitespace-nowrap">{fmtDate(it.updated_at || it.created_at)}</td>
                    <td className="px-4 py-3">
                      {(it.status || 'active').toLowerCase() === 'active' && it.id ? (
                        <button
                          type="button"
                          disabled={archivingId === it.id}
                          onClick={() => archiveItem(it.id!)}
                          className="px-3 py-1 rounded-lg text-xs font-medium border border-amber-500/30 text-amber-500 hover:bg-amber-500/10 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          {archivingId === it.id ? '…' : 'Archive'}
                        </button>
                      ) : (
                        <span className="text-slate-700 text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
