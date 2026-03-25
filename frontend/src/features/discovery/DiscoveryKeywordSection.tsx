/** Step 239/240: Keyword discovery results section. */
import type { DiscoveryKeywordItem } from '../../types/api'
import { KeywordResultCard } from './DiscoveryResultCard'

const sectionStyle: React.CSSProperties = {
  marginBottom: '1.5rem',
}

const titleStyle: React.CSSProperties = {
  margin: '0 0 0.5rem',
  fontSize: '1rem',
  fontWeight: 600,
}

export default function DiscoveryKeywordSection({ items, workspaceId }: { items: DiscoveryKeywordItem[]; workspaceId?: number }) {
  const list = Array.isArray(items) ? items : []
  if (list.length === 0) return null
  return (
    <section style={sectionStyle} aria-label="Keyword discovery results">
      <h2 style={titleStyle}>Keyword discovery</h2>
      <div>
        {list.map((item, i) => (
          <KeywordResultCard key={i} item={item} workspaceId={workspaceId} />
        ))}
      </div>
    </section>
  )
}
