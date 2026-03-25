/** API response shapes from FastAPI gateway (Step 231/232). */

export interface HealthResponse {
  status: string
  service: string
  timestamp: string
  db_ok?: boolean | null
}

export interface DashboardOverview {
  total_opportunities?: number
  high_priority_opportunities?: number
  total_portfolio_items?: number
  high_risk_item_count?: number
  top_strategic_score_count?: number
  last_updated?: string | null
}

export interface DashboardPayload {
  workspace_id?: number
  generated_at?: string
  overview?: DashboardOverview
  intelligence_summary?: Record<string, unknown>
  strategy_summary?: Record<string, unknown>
  portfolio_summary?: Record<string, unknown>
  risk_summary?: Record<string, unknown>
  market_summary?: Record<string, unknown>
  activity_summary?: Record<string, unknown>
  top_items?: {
    top_opportunities?: OpportunityItem[]
    top_recommendations?: unknown[]
    top_risks?: unknown[]
    top_markets?: unknown[]
  }
  top_actions?: unknown[]
  notices?: unknown[]
  health_indicators?: Record<string, unknown>
}

export interface OpportunityItem {
  opportunity_id?: string | number | null
  strategy_status?: string
  priority_level?: string
  opportunity_score?: number | null
  rationale?: string
  recommended_action?: string
  risk_notes?: unknown[]
}

export interface DashboardResponse {
  data?: DashboardPayload | null
  meta?: { workspace_id?: number }
  error?: string
}

export interface OpportunitiesResponse {
  data?: OpportunityItem[]
  meta?: { workspace_id?: number; count?: number }
  error?: string
}

export interface PortfolioItem {
  id?: number
  workspace_id?: number
  item_type?: string
  item_key?: string
  item_label?: string
  source_type?: string
  status?: string
  created_at?: string
  updated_at?: string
}

export interface PortfolioSummary {
  total?: number
  by_status?: Record<string, number>
  by_type?: Record<string, number>
}

export interface PortfolioSummaryResponse {
  data?: PortfolioSummary | null
  meta?: { workspace_id?: number }
  error?: string
}

export interface PortfolioListResponse {
  data?: PortfolioItem[]
  meta?: { workspace_id?: number; count?: number; limit?: number }
  error?: string
}

export interface AlertItem {
  id?: number
  alert_type?: string
  severity?: string
  title?: string
  description?: string
  recorded_at?: string
  read_at?: string | null
}

export interface AlertsResponse {
  data?: AlertItem[]
  meta?: { workspace_id?: number; count?: number }
  error?: string
}

export interface StrategySummaryResponse {
  data?: Record<string, unknown> | null
  meta?: { workspace_id?: number }
  error?: string
}

/** Step 238/239: Discovery API (keyword / market). */
export interface DiscoveryKeywordItem {
  keyword?: string | null
  market?: string | null
  category?: string | null
  result_count?: number
  opportunity_count?: number
  top_opportunity_refs?: string[]
  last_observed_at?: string | null
}

export interface DiscoveryMarketItem {
  market_key?: string | null
  discovery_count?: number
  top_categories?: string[]
  top_opportunities?: string[]
  signal_summary?: Record<string, unknown>
  last_observed_at?: string | null
}

export interface DiscoveryKeywordsResponse {
  data?: DiscoveryKeywordItem[]
  meta?: { workspace_id?: number; count?: number }
  error?: string
}

export interface DiscoveryMarketsResponse {
  data?: DiscoveryMarketItem[]
  meta?: { workspace_id?: number; count?: number }
  error?: string
}

/** Steps 243–245: Discovery cluster (GET /discovery/clusters). */
export interface DiscoveryCluster {
  cluster_id?: string
  cluster_label?: string
  keyword_count?: number
  opportunity_count?: number
  top_keywords?: string[]
  top_opportunities?: string[]
}

/** Steps 243–245: Category explorer (GET /discovery/category-explorer). */
export interface CategoryExplorerItem {
  category?: string
  opportunity_count?: number
  keyword_count?: number
  top_opportunities?: string[]
  top_keywords?: string[]
}

/** Steps 246–248: Opportunity timeline (GET /opportunities/{id}/timeline). */
export interface OpportunityTimelineData {
  timeline_points?: { observed_at?: string; score?: number; rank?: number }[]
  score_changes?: { at?: string; score?: number }[]
  rank_changes?: { at?: string; rank?: number }[]
  observed_timestamps?: string[]
}

/** Steps 246–248: Saved search. */
export interface SavedSearch {
  id?: number
  label?: string
  query?: string
  market?: string | null
  category?: string | null
  limit?: number
  sort?: string
  created_at?: string
}

/** Steps 249–250: Research session. */
export interface ResearchSession {
  id?: number
  label?: string
  created_at?: string
  attached_searches?: unknown[]
  attached_opportunities?: unknown[]
  notes_summary?: string | null
}

/** Steps 249–250: Research performance metrics. */
export interface ResearchMetrics {
  total_discovery_queries?: number
  total_opportunities_found?: number
  total_converted_opportunities?: number
  total_watchlisted?: number
  average_score?: number | null
  top_markets?: string[]
  top_categories?: string[]
  last_refreshed_at?: string | null
}

/** Steps 246–248: Discovery alert rule. */
export interface DiscoveryAlertRule {
  id?: number
  keyword?: string | null
  market?: string | null
  category?: string | null
  min_score?: number | null
  min_opportunity_count?: number | null
  enabled?: boolean
}

/** Steps 243–245: Opportunity compare (POST /opportunities/compare). */
export interface OpportunityCompareResult {
  compared_items?: { opportunity_id?: number; title?: string; score?: number; priority?: string; ranking_position?: number; risk_indicator?: string }[]
  score_comparison?: { opportunity_id?: number; score?: number }[]
  risk_comparison?: { opportunity_id?: number; risk_indicator?: string }[]
  ranking_comparison?: { opportunity_id?: number; ranking_position?: number }[]
}

/** Pipeline: Opportunity detail (GET /opportunities/{id}). */
export interface OpportunityDetail {
  id?: number
  title?: string
  score?: number | null
  priority?: string
  ranking_position?: number | null
  rationale_summary?: string
  recommended_action?: string
  risk_indicator?: string
  market?: string
  category?: string
  history?: unknown[]
}
