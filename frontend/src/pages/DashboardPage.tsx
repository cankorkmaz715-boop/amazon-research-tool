import { useState, useEffect } from 'react'
import { api, getApiBaseUrl } from '../lib/api'
import type {
  HealthResponse,
  DashboardResponse,
  OpportunitiesResponse,
  PortfolioSummaryResponse,
  AlertsResponse,
  StrategySummaryResponse,
} from '../types/api'
import HealthCard from '../components/HealthCard'
import OverviewCard from '../components/OverviewCard'
import OpportunityList from '../components/OpportunityList'
import PortfolioSummaryCard from '../components/PortfolioSummaryCard'
import AlertsCard from '../components/AlertsCard'
import StrategySummaryCard from '../components/StrategySummaryCard'

const DEFAULT_WORKSPACE_ID = 1

export interface DashboardPageProps {
  workspaceId?: number
}

export default function DashboardPage({ workspaceId: propWorkspaceId }: DashboardPageProps = {}) {
  const [workspaceId, setWorkspaceId] = useState(propWorkspaceId ?? DEFAULT_WORKSPACE_ID)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [opportunities, setOpportunities] = useState<OpportunitiesResponse | null>(null)
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummaryResponse | null>(null)
  const [alerts, setAlerts] = useState<AlertsResponse | null>(null)
  const [strategy, setStrategy] = useState<StrategySummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    setHealth(null)
    setHealthError(null)
    setDashboard(null)
    setOpportunities(null)
    setPortfolioSummary(null)
    setAlerts(null)
    setStrategy(null)

    const wid = propWorkspaceId !== undefined ? propWorkspaceId : workspaceId
    Promise.all([
      api.getHealth().catch((e) => {
        if (!cancelled) setHealthError(e instanceof Error ? e.message : String(e))
        return null
      }),
      api.getDashboard(wid).catch(() => null),
      api.getOpportunities(wid).catch(() => null),
      api.getPortfolioSummary(wid).catch(() => null),
      api.getAlerts(wid).catch(() => null),
      api.getStrategySummary(wid).catch(() => null),
    ]).then(([h, d, o, p, a, s]) => {
      if (cancelled) return
      if (h) setHealth(h)
      if (d) setDashboard(d)
      if (o) setOpportunities(o)
      if (p) setPortfolioSummary(p)
      if (a) setAlerts(a)
      if (s) setStrategy(s)
      if (!d?.data && !d?.error) setError('Dashboard unavailable')
      setLoading(false)
    })

    return () => { cancelled = true }
  }, [propWorkspaceId, workspaceId])

  return (
    <div>
      {propWorkspaceId === undefined && (
        <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <label>
            Workspace ID:{' '}
            <input
              type="number"
              min={1}
              value={workspaceId}
              onChange={(e) => setWorkspaceId(Number(e.target.value) || DEFAULT_WORKSPACE_ID)}
              style={{ width: 80, padding: '0.35rem 0.5rem' }}
            />
          </label>
          <span style={{ fontSize: '0.8rem', color: '#666' }}>API: {getApiBaseUrl()}</span>
        </div>
      )}

      {loading && <p>Loading…</p>}
      {error && !loading && <p style={{ color: '#c00' }}>{error}</p>}

      {!loading && (
        <>
          <HealthCard health={health} error={healthError} />
          <OverviewCard data={dashboard?.data?.overview} />
          <OpportunityList items={opportunities?.data ?? dashboard?.data?.top_items?.top_opportunities} />
          <PortfolioSummaryCard data={portfolioSummary?.data ?? dashboard?.data?.portfolio_summary} />
          <AlertsCard items={alerts?.data} />
          <StrategySummaryCard data={strategy?.data} />
        </>
      )}
    </div>
  )
}
