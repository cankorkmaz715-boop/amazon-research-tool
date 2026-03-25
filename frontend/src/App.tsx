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

const DEFAULT_WORKSPACE_ID = 1

export default function App() {
  const [view, setView] = useState<'dashboard' | 'discovery' | 'opportunity' | 'clusters' | 'categories' | 'compare' | 'analytics' | 'sessions' | 'metrics'>('dashboard')
  const [workspaceId, setWorkspaceId] = useState(DEFAULT_WORKSPACE_ID)
  const [opportunityId, setOpportunityId] = useState(1)

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '1px solid #ddd', paddingBottom: '0.75rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem' }}>Amazon Research Dashboard</h1>
        <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#666' }}>
          Live workspace panel (Step 233)
        </p>
        <nav style={{ marginTop: '0.75rem', display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setView('dashboard')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'dashboard' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Dashboard
          </button>
          <button
            type="button"
            onClick={() => setView('discovery')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'discovery' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Discovery
          </button>
          <button
            type="button"
            onClick={() => setView('opportunity')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'opportunity' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Opportunity
          </button>
          <button
            type="button"
            onClick={() => setView('clusters')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'clusters' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Clusters
          </button>
          <button
            type="button"
            onClick={() => setView('categories')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'categories' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Categories
          </button>
          <button
            type="button"
            onClick={() => setView('compare')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'compare' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Compare
          </button>
          <button
            type="button"
            onClick={() => setView('analytics')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'analytics' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Analytics
          </button>
          <button
            type="button"
            onClick={() => setView('sessions')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'sessions' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Sessions
          </button>
          <button
            type="button"
            onClick={() => setView('metrics')}
            style={{
              padding: '0.35rem 0.75rem',
              fontWeight: view === 'metrics' ? 600 : 400,
              cursor: 'pointer',
            }}
          >
            Metrics
          </button>
          <label style={{ marginLeft: '0.5rem', fontSize: '0.875rem' }}>
            Workspace ID:{' '}
            <input
              type="number"
              min={1}
              value={workspaceId}
              onChange={(e) => setWorkspaceId(Number(e.target.value) || DEFAULT_WORKSPACE_ID)}
              style={{ width: 60, padding: '0.25rem 0.5rem' }}
            />
          </label>
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
              Opportunity ID (for timeline):{' '}
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
    </main>
  )
}
