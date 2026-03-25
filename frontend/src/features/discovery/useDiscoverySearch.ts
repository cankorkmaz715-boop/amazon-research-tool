/**
 * Step 239: Discovery search hook – fetches keywords and markets from API.
 * Workspace-scoped; no backend logic duplication.
 */
import { useState, useCallback } from 'react'
import { api } from '../../lib/api'
import type { DiscoveryKeywordItem, DiscoveryMarketItem } from '../../types/api'

export interface DiscoverySearchParams {
  q?: string
  market?: string
  category?: string
  limit?: number
  sort?: string
}

export interface DiscoverySearchState {
  keywordResults: DiscoveryKeywordItem[]
  marketResults: DiscoveryMarketItem[]
  loading: boolean
  error: string | null
}

export function useDiscoverySearch(workspaceId: number) {
  const [keywordResults, setKeywordResults] = useState<DiscoveryKeywordItem[]>([])
  const [marketResults, setMarketResults] = useState<DiscoveryMarketItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const runSearch = useCallback(
    async (params: DiscoverySearchParams = {}) => {
      setLoading(true)
      setError(null)
      setKeywordResults([])
      setMarketResults([])
      try {
        const [kwRes, mkRes] = await Promise.all([
          api
            .getDiscoveryKeywords(workspaceId, {
              q: params.q,
              market: params.market,
              limit: params.limit ?? 50,
              sort: params.sort ?? 'recent',
            })
            .catch((e) => ({ data: [], meta: { count: 0 }, error: e instanceof Error ? e.message : String(e) })),
          api
            .getDiscoveryMarkets(workspaceId, {
              category: params.category,
              limit: params.limit ?? 20,
            })
            .catch((e) => ({ data: [], meta: { count: 0 }, error: e instanceof Error ? e.message : String(e) })),
        ])
        const kwData = Array.isArray((kwRes as { data?: unknown }).data) ? (kwRes as { data: DiscoveryKeywordItem[] }).data : []
        const mkData = Array.isArray((mkRes as { data?: unknown }).data) ? (mkRes as { data: DiscoveryMarketItem[] }).data : []
        setKeywordResults(kwData)
        setMarketResults(mkData)
        const err = (kwRes as { error?: string }).error || (mkRes as { error?: string }).error
        if (err) setError(err)
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setLoading(false)
      }
    },
    [workspaceId]
  )

  return {
    keywordResults,
    marketResults,
    loading,
    error,
    runSearch,
  }
}
