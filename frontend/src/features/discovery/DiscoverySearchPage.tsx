/**
 * Step 239: Discovery search page – keyword and market discovery from live API.
 * Workspace-scoped; loading, empty, error states; partial-data resilient.
 */
import { useState, useCallback } from 'react'
import { useDiscoverySearch } from './useDiscoverySearch'
import DiscoverySearchBar from './DiscoverySearchBar'
import DiscoveryFilters from './DiscoveryFilters'
import DiscoveryResultsList from './DiscoveryResultsList'
import DiscoveryLoadingState from './DiscoveryLoadingState'
import DiscoveryErrorState from './DiscoveryErrorState'

const DEFAULT_WORKSPACE_ID = 1
const pageStyle: React.CSSProperties = { marginBottom: '1.5rem' }
const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
}

export interface DiscoverySearchPageProps {
  workspaceId?: number
}

export default function DiscoverySearchPage({ workspaceId: propWorkspaceId }: DiscoverySearchPageProps) {
  const workspaceId = propWorkspaceId ?? DEFAULT_WORKSPACE_ID
  const [query, setQuery] = useState('')
  const [market, setMarket] = useState('')
  const [category, setCategory] = useState('')
  const [limit, setLimit] = useState(50)

  const { keywordResults, marketResults, loading, error, runSearch } = useDiscoverySearch(workspaceId)

  const handleSearch = useCallback(() => {
    runSearch({ q: query.trim() || undefined, market: market || undefined, category: category.trim() || undefined, limit, sort: 'recent' })
  }, [query, market, category, limit, runSearch])

  return (
    <div style={pageStyle} data-testid="discovery-search-page">
      <div style={cardStyle}>
        <h2 style={{ margin: '0 0 0.75rem', fontSize: '1.1rem' }}>Discovery search</h2>
        <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: '#666' }}>
          Workspace {workspaceId} · Keyword and market discovery from the live API.
        </p>
        <DiscoverySearchBar
          query={query}
          onQueryChange={setQuery}
          onSearch={handleSearch}
          disabled={loading}
        />
        <DiscoveryFilters
          market={market}
          onMarketChange={setMarket}
          category={category}
          onCategoryChange={setCategory}
          limit={limit}
          onLimitChange={setLimit}
        />
      </div>

      {error && <DiscoveryErrorState message={error} />}
      {loading && <DiscoveryLoadingState />}
      {!loading && !error && (
        <DiscoveryResultsList
          keywordResults={keywordResults}
          marketResults={marketResults}
          workspaceId={workspaceId}
        />
      )}
    </div>
  )
}
