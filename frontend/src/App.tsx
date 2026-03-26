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
  | 'dashboard'
  | 'discovery'
  | 'opportunity'
  | 'clusters'
  | 'categories'
  | 'compare'
  | 'analytics'
  | 'sessions'
  | 'metrics'
  | 'alerts'
  | 'portfolio'
  | 'settings'

const NAV_ITEMS: { view: View; label: string }[] = [
  { view: 'dashboard', label: 'Dashboard' },
  { view: 'discovery', label: 'Discovery' },
  { view: 'opportunity', label: 'Opportunity' },
  { view: 'clusters', label: 'Clusters' },
  { view: 'categories', label: 'Categories' },
  { view: 'compare', label: 'Compare' },
  { view: 'analytics', label: 'Analytics' },
  { view: 'sessions', label: 'Sessions' },
  { view: 'metrics', label: 'Metrics' },
  { view: 'alerts', label: 'Alerts' },
  { view: 'portfolio', label: 'Portfolio' },
  { view: 'settings', label: 'Settings' },
]

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  const [workspaceId, setWorkspaceId] = useState(DEFAULT_WORKSPACE_ID)
  const [opportunityId, setOpportunityId] = useState(1)

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '1px solid #ddd', paddingBottom: '0.75rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Amazon Research Dashboard</h1>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#666' }}>
          Live workspace panel
        </p>
        <nav style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {NAV_ITEMS.map(({ view: v, label }) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              style={{
                padding: '0.35rem 0.75rem',
                fontWeight: view === v ? 700 : 400,
                cursor: 'pointer',
                borderRadius: 4,
                border: view === v ? '1px solid #0063cc' : '1px solid #ccc',
                background: view === v ? '#e7f1ff' : '#fff',
                color: view === v ? '#0046a8' : '#333',
                fontSize: '0.875rem',
              }}
            >
              {label}
            </button>
          ))}
          {view !== 'settings' && (
            <label style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>
              Workspace:{' '}
              <input
                type="number"
                min={1}
                value={workspaceId}
                onChange={(e) => setWorkspaceId(Number(e.target.value) || DEFAULT_WORKSPACE_ID)}
                style={{ width: 60, padding: '0.25rem 0.5rem' }}
              />
            </label>
          )}
        </nav>
      </header>

      {view === 'dashboard' && <DashboardPage workspaceId={workspaceId} />}

      {view === 'discovery' && <DiscoverySearchPage workspaceId={workspaceId} />}

      {view === 'opportunity' && (
        <div>
          <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <label style={{ fontSize: '0.875rem' }}>
              Opportunity ID:{' '}
              <input
                type="number"
                min={1}
                value={opportunityId}
                onChange={(e) => setOpportunityId(Number(e.target.value) || 1)}
                style={{ width: 80, padding: '0.25rem 0.5rem' }}
              />
            </label>
          </div>
          <OpportunityDetailPage workspaceId={workspaceId} opportunityId={opportunityId} />
        </div>
      )}

      {view === 'clusters' && <DiscoveryClustersPage workspaceId={workspaceId} />}
      {view === 'categories' && <CategoryExplorerPage workspaceId={workspaceId} />}
      {view === 'compare' && <OpportunityComparisonPage workspaceId={workspaceId} />}

      {view === 'analytics' && (
        <div>
          <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.875rem' }}>
              Opportunity ID:{' '}
              <input
                type="number"
                min={1}
                value={opportunityId}
                onChange={(e) => setOpportunityId(Number(e.target.value) || 1)}
                style={{ width: 80, padding: '0.25rem 0.5rem' }}
              />
            </label>
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
  )
}
