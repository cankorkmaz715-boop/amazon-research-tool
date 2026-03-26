import { useState } from 'react'
import DashboardPage from './pages/DashboardPage'
import DiscoverySearchPage from './features/discovery/DiscoverySearchPage'
import OpportunityDetailPage from './pages/opportunity/OpportunityDetailPage'
import DiscoveryClustersPage from './pages/discovery/DiscoveryClustersPage'
import CategoryExplorerPage from './pages/discovery/CategoryExplorerPage'
import OpportunityComparisonPage from './pages/opportunity/OpportunityComparisonPage'
import OpportunityAnalyticsPage from './pages/analytics/OpportunityAnalyticsPage'
import ResearchSessionsPage from './pages/research/ResearchSessionsPage'
import ResearchMetricsPage from './pages/research/ResearchMetricsPage'
import AlertCenterPage from './pages/AlertCenterPage'
import PortfolioPage from './pages/PortfolioPage'
import SettingsPage from './pages/SettingsPage'

const DEFAULT_WORKSPACE_ID = 1

type View =
  | 'dashboard' | 'discovery' | 'opportunity' | 'clusters'
  | 'categories' | 'compare' | 'analytics' | 'sessions'
  | 'metrics' | 'alerts' | 'portfolio' | 'settings'

const NAV_GROUPS: { label: string; items: { view: View; label: string; icon: string }[] }[] = [
  {
    label: 'Core',
    items: [
      { view: 'dashboard', label: 'Dashboard', icon: '◈' },
      { view: 'portfolio', label: 'Portfolio', icon: '📁' },
      { view: 'alerts', label: 'Alerts', icon: '🔔' },
    ],
  },
  {
    label: 'Research',
    items: [
      { view: 'discovery', label: 'Discovery', icon: '🔍' },
      { view: 'clusters', label: 'Clusters', icon: '⬡' },
      { view: 'categories', label: 'Categories', icon: '⊞' },
      { view: 'analytics', label: 'Analytics', icon: '📈' },
      { view: 'sessions', label: 'Sessions', icon: '🗂' },
      { view: 'metrics', label: 'Metrics', icon: '📊' },
    ],
  },
  {
    label: 'Opportunity',
    items: [
      { view: 'opportunity', label: 'Detail', icon: '💡' },
      { view: 'compare', label: 'Compare', icon: '⇌' },
    ],
  },
  {
    label: 'System',
    items: [
      { view: 'settings', label: 'Settings', icon: '⚙' },
    ],
  },
]

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  const [workspaceId, setWorkspaceId] = useState(DEFAULT_WORKSPACE_ID)
  const [opportunityId, setOpportunityId] = useState(1)

  return (
    <div className="min-h-screen bg-[#03060f]">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-violet-600/10 rounded-full blur-3xl" />
        <div className="absolute top-20 right-0 w-80 h-80 bg-indigo-600/8 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-1/3 w-64 h-64 bg-fuchsia-600/5 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[#03060f]/80 backdrop-blur-xl">
        <div className="max-w-[1400px] mx-auto px-4 py-0">
          <div className="flex items-center gap-8 h-14">
            {/* Logo */}
            <div className="flex items-center gap-2.5 shrink-0">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
                <span className="text-white text-xs font-bold">A</span>
              </div>
              <span className="text-sm font-bold text-slate-100 tracking-tight">Amazon Research</span>
            </div>

            {/* Nav groups */}
            <nav className="flex items-center gap-1 flex-1 overflow-x-auto scrollbar-thin py-2">
              {NAV_GROUPS.map((group, gi) => (
                <div key={group.label} className={`flex items-center gap-1 ${gi > 0 ? 'ml-3 pl-3 border-l border-white/[0.07]' : ''}`}>
                  {group.items.map(({ view: v, label }) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setView(v)}
                      className={`
                        flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-200
                        ${view === v
                          ? 'bg-gradient-to-r from-violet-600/20 to-indigo-600/20 text-violet-300 border border-violet-500/30 shadow-sm shadow-violet-500/10'
                          : 'text-slate-500 hover:text-slate-300 hover:bg-white/5 border border-transparent'
                        }
                      `}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              ))}
            </nav>

            {/* Workspace input */}
            {view !== 'settings' && (
              <div className="shrink-0 flex items-center gap-2">
                <span className="text-xs text-slate-600 font-medium">WS</span>
                <input
                  type="number"
                  min={1}
                  value={workspaceId}
                  onChange={(e) => setWorkspaceId(Number(e.target.value) || DEFAULT_WORKSPACE_ID)}
                  className="w-14 px-2 py-1 text-xs text-slate-300 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all text-center"
                />
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-[1400px] mx-auto px-4 py-6 relative z-10">
        {view === 'dashboard' && <DashboardPage workspaceId={workspaceId} />}
        {view === 'discovery' && <DiscoverySearchPage workspaceId={workspaceId} />}

        {view === 'opportunity' && (
          <div>
            <div className="mb-4 flex items-center gap-3">
              <span className="text-sm text-slate-500">Opportunity ID:</span>
              <input
                type="number"
                min={1}
                value={opportunityId}
                onChange={(e) => setOpportunityId(Number(e.target.value) || 1)}
                className="w-20 px-2 py-1 text-sm text-slate-300 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-violet-500/50 transition-all text-center"
              />
            </div>
            <OpportunityDetailPage workspaceId={workspaceId} opportunityId={opportunityId} />
          </div>
        )}

        {view === 'clusters' && <DiscoveryClustersPage workspaceId={workspaceId} />}
        {view === 'categories' && <CategoryExplorerPage workspaceId={workspaceId} />}
        {view === 'compare' && <OpportunityComparisonPage workspaceId={workspaceId} />}

        {view === 'analytics' && (
          <div>
            <div className="mb-4 flex items-center gap-3">
              <span className="text-sm text-slate-500">Opportunity ID:</span>
              <input
                type="number"
                min={1}
                value={opportunityId}
                onChange={(e) => setOpportunityId(Number(e.target.value) || 1)}
                className="w-20 px-2 py-1 text-sm text-slate-300 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-violet-500/50 transition-all text-center"
              />
            </div>
            <OpportunityAnalyticsPage workspaceId={workspaceId} opportunityId={opportunityId} />
          </div>
        )}

        {view === 'sessions' && <ResearchSessionsPage workspaceId={workspaceId} />}
        {view === 'metrics' && <ResearchMetricsPage workspaceId={workspaceId} />}
        {view === 'alerts' && <AlertCenterPage workspaceId={workspaceId} />}
        {view === 'portfolio' && <PortfolioPage workspaceId={workspaceId} />}
        {view === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
