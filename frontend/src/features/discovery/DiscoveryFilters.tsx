/**
 * Step 239: Discovery filters – market, optional category, limit.
 * Controlled inputs; no submit – parent triggers search.
 */
export interface DiscoveryFiltersProps {
  market: string
  onMarketChange: (v: string) => void
  category: string
  onCategoryChange: (v: string) => void
  limit: number
  onLimitChange: (v: number) => void
}

const rowStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: '1rem',
  marginBottom: '0.75rem',
}

const labelStyle: React.CSSProperties = {
  fontSize: '0.875rem',
  marginRight: '0.25rem',
}

export default function DiscoveryFilters({
  market,
  onMarketChange,
  category,
  onCategoryChange,
  limit,
  onLimitChange,
}: DiscoveryFiltersProps) {
  return (
    <div style={rowStyle} role="group" aria-label="Discovery filters">
      <label style={labelStyle}>
        Market
        <select
          value={market}
          onChange={(e) => onMarketChange(e.target.value)}
          style={{ marginLeft: '0.35rem', padding: '0.35rem 0.5rem' }}
          aria-label="Filter by market"
        >
          <option value="">All</option>
          <option value="DE">DE</option>
          <option value="US">US</option>
          <option value="AU">AU</option>
        </select>
      </label>
      <label style={labelStyle}>
        Category
        <input
          type="text"
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
          placeholder="Optional"
          style={{ marginLeft: '0.35rem', padding: '0.35rem 0.5rem', width: 120 }}
          aria-label="Filter by category"
        />
      </label>
      <label style={labelStyle}>
        Limit
        <select
          value={limit}
          onChange={(e) => onLimitChange(Number(e.target.value))}
          style={{ marginLeft: '0.35rem', padding: '0.35rem 0.5rem' }}
          aria-label="Result limit"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </label>
    </div>
  )
}
