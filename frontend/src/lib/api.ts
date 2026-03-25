/**
 * API client for FastAPI gateway. Uses VITE_API_BASE_URL.
 * Step 233: Dashboard UI – live workspace panel.
 */

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

function url(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`
  return baseUrl ? `${baseUrl.replace(/\/$/, '')}${p}` : p
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(url(path), { method: 'GET', headers: { Accept: 'application/json' } })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? res.statusText)
  return data as T
}

async function post<T>(path: string, body: object): Promise<T> {
  const res = await fetch(url(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error((data as { detail?: string }).detail ?? res.statusText)
  return data as T
}

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') search.set(k, String(v))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  getHealth: () => get<import('../types/api').HealthResponse>('/health'),
  getDashboard: (workspaceId: number) =>
    get<import('../types/api').DashboardResponse>(`/api/workspaces/${workspaceId}/dashboard`),
  getOpportunities: (workspaceId: number) =>
    get<import('../types/api').OpportunitiesResponse>(`/api/workspaces/${workspaceId}/opportunities`),
  getPortfolioSummary: (workspaceId: number) =>
    get<import('../types/api').PortfolioSummaryResponse>(`/api/workspaces/${workspaceId}/portfolio/summary`),
  getAlerts: (workspaceId: number) =>
    get<import('../types/api').AlertsResponse>(`/api/workspaces/${workspaceId}/alerts`),
  getStrategySummary: (workspaceId: number) =>
    get<import('../types/api').StrategySummaryResponse>(`/api/workspaces/${workspaceId}/strategy/summary`),
  /** Step 239: Discovery search API (Step 238). */
  getDiscoveryKeywords: (workspaceId: number, params?: { q?: string; market?: string; limit?: number; sort?: string }) =>
    get<import('../types/api').DiscoveryKeywordsResponse>(
      `/api/workspaces/${workspaceId}/discovery/keywords${buildQuery(params ?? {})}`
    ),
  getDiscoveryMarkets: (workspaceId: number, params?: { category?: string; limit?: number }) =>
    get<import('../types/api').DiscoveryMarketsResponse>(
      `/api/workspaces/${workspaceId}/discovery/markets${buildQuery(params ?? {})}`
    ),
  /** Step 240: Convert discovery result to opportunity. */
  postOpportunityFromDiscovery: (workspaceId: number, payload: { discovery_id?: string; keyword?: string; market?: string; category?: string; source_metadata?: Record<string, unknown> }) =>
    post<{ data: { opportunity_id?: number; status: string; message: string }; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/opportunities/from-discovery`,
      payload
    ),
  /** Pipeline: Opportunity detail. */
  getOpportunityDetail: (workspaceId: number, opportunityId: number) =>
    get<{ data: import('../types/api').OpportunityDetail; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/opportunities/${opportunityId}`
    ),
  postOpportunityWatch: (workspaceId: number, opportunityId: number) =>
    post<{ data: { watched: boolean; portfolio_id?: number; created?: boolean }; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/opportunities/${opportunityId}/watch`,
      {}
    ),
  deleteOpportunityWatch: (workspaceId: number, opportunityId: number) =>
    fetch(url(`/api/workspaces/${workspaceId}/opportunities/${opportunityId}/watch`), { method: 'DELETE', headers: { Accept: 'application/json' } }).then(async (res) => {
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error((data as { detail?: string }).detail ?? res.statusText)
      return data as { data: { watched: boolean; removed: boolean }; meta?: { workspace_id?: number } }
    }),
  /** Steps 243–245: Research intelligence. */
  getDiscoveryClusters: (workspaceId: number) =>
    get<{ data: import('../types/api').DiscoveryCluster[]; meta?: { workspace_id?: number; count?: number } }>(
      `/api/workspaces/${workspaceId}/discovery/clusters`
    ),
  getDiscoveryCategoryExplorer: (workspaceId: number) =>
    get<{ data: import('../types/api').CategoryExplorerItem[]; meta?: { workspace_id?: number; count?: number } }>(
      `/api/workspaces/${workspaceId}/discovery/category-explorer`
    ),
  postOpportunitiesCompare: (workspaceId: number, opportunityIds: number[]) =>
    post<{ data: import('../types/api').OpportunityCompareResult; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/opportunities/compare`,
      { opportunity_ids: opportunityIds }
    ),
  /** Steps 246–248: Opportunity analytics. */
  getOpportunityTimeline: (workspaceId: number, opportunityId: number) =>
    get<{ data: import('../types/api').OpportunityTimelineData; meta?: { workspace_id?: number; opportunity_id?: number } }>(
      `/api/workspaces/${workspaceId}/opportunities/${opportunityId}/timeline`
    ),
  getSavedSearches: (workspaceId: number) =>
    get<{ data: import('../types/api').SavedSearch[]; meta?: { workspace_id?: number; count?: number } }>(
      `/api/workspaces/${workspaceId}/saved-searches`
    ),
  postSavedSearch: (workspaceId: number, payload: { label: string; query?: string; market?: string; category?: string; limit?: number; sort?: string }) =>
    post<{ data: import('../types/api').SavedSearch; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/saved-searches`,
      payload
    ),
  deleteSavedSearch: (workspaceId: number, searchId: number) =>
    fetch(url(`/api/workspaces/${workspaceId}/saved-searches/${searchId}`), { method: 'DELETE', headers: { Accept: 'application/json' } }).then(async (res) => {
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error((data as { detail?: string }).detail ?? res.statusText)
      return data as { data: { removed: boolean }; meta?: { workspace_id?: number } }
    }),
  getDiscoveryAlertRules: (workspaceId: number) =>
    get<{ data: import('../types/api').DiscoveryAlertRule[]; meta?: { workspace_id?: number; count?: number } }>(
      `/api/workspaces/${workspaceId}/discovery-alert-rules`
    ),
  postDiscoveryAlertRule: (workspaceId: number, payload: { keyword?: string; market?: string; category?: string; min_score?: number; min_opportunity_count?: number; enabled?: boolean }) =>
    post<{ data: import('../types/api').DiscoveryAlertRule; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/discovery-alert-rules`,
      payload
    ),
  deleteDiscoveryAlertRule: (workspaceId: number, ruleId: number) =>
    fetch(url(`/api/workspaces/${workspaceId}/discovery-alert-rules/${ruleId}`), { method: 'DELETE', headers: { Accept: 'application/json' } }).then(async (res) => {
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error((data as { detail?: string }).detail ?? res.statusText)
      return data as { data: { removed: boolean }; meta?: { workspace_id?: number } }
    }),
  /** Steps 249–250: Research workspace. */
  getResearchSessions: (workspaceId: number) =>
    get<{ data: import('../types/api').ResearchSession[]; meta?: { workspace_id?: number; count?: number } }>(
      `/api/workspaces/${workspaceId}/research-sessions`
    ),
  postResearchSession: (workspaceId: number, payload: { label?: string; attached_searches?: unknown[]; attached_opportunities?: unknown[]; notes_summary?: string }) =>
    post<{ data: import('../types/api').ResearchSession; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/research-sessions`,
      payload
    ),
  getResearchSession: (workspaceId: number, sessionId: number) =>
    get<{ data: import('../types/api').ResearchSession; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/research-sessions/${sessionId}`
    ),
  getResearchMetrics: (workspaceId: number) =>
    get<{ data: import('../types/api').ResearchMetrics; meta?: { workspace_id?: number } }>(
      `/api/workspaces/${workspaceId}/research/metrics`
    ),
}

export function getApiBaseUrl(): string {
  return baseUrl || '(same origin)'
}
