/** Steps 243–245: Category opportunity explorer page. */
import { useState, useEffect } from 'react'
import { api } from '../../lib/api'
import type { CategoryExplorerItem } from '../../types/api'
import CategoryExplorerCard from '../../components/discovery/CategoryExplorerCard'

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
}

export interface CategoryExplorerPageProps {
  workspaceId: number
}

export default function CategoryExplorerPage({ workspaceId }: CategoryExplorerPageProps) {
  const [items, setItems] = useState<CategoryExplorerItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    api
      .getDiscoveryCategoryExplorer(workspaceId)
      .then((res) => { if (!cancelled && res?.data) setItems(Array.isArray(res.data) ? res.data : []) })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [workspaceId])

  if (loading) return <div style={cardStyle}>Loading category explorer…</div>
  if (error) return <div style={{ ...cardStyle, color: '#b91c1c' }}>{error}</div>
  if (items.length === 0) return <div style={cardStyle}>No categories.</div>
  return (
    <div>
      <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem' }}>Category opportunity explorer</h2>
      {items.map((item, i) => (
        <CategoryExplorerCard key={item.category ?? i} item={item} />
      ))}
    </div>
  )
}
