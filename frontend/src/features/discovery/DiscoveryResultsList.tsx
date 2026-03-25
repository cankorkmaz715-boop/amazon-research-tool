/** Step 239/240: Combined keyword + market discovery results. */
import type { DiscoveryKeywordItem, DiscoveryMarketItem } from '../../types/api'
import DiscoveryKeywordSection from './DiscoveryKeywordSection'
import DiscoveryMarketSection from './DiscoveryMarketSection'
import DiscoveryEmptyState from './DiscoveryEmptyState'

export default function DiscoveryResultsList({
  keywordResults,
  marketResults,
  workspaceId,
}: {
  keywordResults: DiscoveryKeywordItem[]
  marketResults: DiscoveryMarketItem[]
  workspaceId?: number
}) {
  const kw = Array.isArray(keywordResults) ? keywordResults : []
  const mk = Array.isArray(marketResults) ? marketResults : []
  const hasAny = kw.length > 0 || mk.length > 0
  if (!hasAny) return <DiscoveryEmptyState />
  return (
    <div>
      <DiscoveryKeywordSection items={kw} workspaceId={workspaceId} />
      <DiscoveryMarketSection items={mk} workspaceId={workspaceId} />
    </div>
  )
}
