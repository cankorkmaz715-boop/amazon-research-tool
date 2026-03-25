/**
 * Step 239: Discovery search bar – keyword query and search trigger.
 */
export interface DiscoverySearchBarProps {
  query: string
  onQueryChange: (v: string) => void
  onSearch: () => void
  disabled?: boolean
}

const wrapStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  alignItems: 'center',
  gap: '0.75rem',
  marginBottom: '1rem',
}

export default function DiscoverySearchBar({ query, onQueryChange, onSearch, disabled }: DiscoverySearchBarProps) {
  return (
    <div style={wrapStyle} role="search" aria-label="Discovery search">
      <input
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        placeholder="Keyword (optional – leave empty for all)"
        style={{ padding: '0.5rem 0.75rem', minWidth: 220 }}
        aria-label="Keyword query"
      />
      <button
        type="button"
        onClick={onSearch}
        disabled={disabled}
        style={{ padding: '0.5rem 1rem', cursor: disabled ? 'not-allowed' : 'pointer' }}
      >
        Search
      </button>
    </div>
  )
}
