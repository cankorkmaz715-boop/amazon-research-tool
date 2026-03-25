/** Step 239/240: Market discovery results section. */
import type { DiscoveryMarketItem } from '../../types/api'
import { MarketResultCard } from './DiscoveryResultCard'

const sectionStyle: React.CSSProperties = {
  marginBottom: '1.5rem',
}

const titleStyle: React.CSSProperties = {
  margin: '0 0 0.5rem',
  fontSize: '1rem',
  fontWeight: 600,
}

export default function DiscoveryMarketSection({ items, workspaceId }: { items: DiscoveryMarketItem[]; workspaceId?: number }) {
  const list = Array.isArray(items) ? items : []
  if (list.length === 0) return null
  return (
    <section style={sectionStyle} aria-label="Market discovery results">
      <h2 style={titleStyle}>Market discovery</h2>
      <div>
        {list.map((item, i) => (
          <MarketResultCard key={i} item={item} workspaceId={workspaceId} />
        ))}
      </div>
    </section>
  )
}
