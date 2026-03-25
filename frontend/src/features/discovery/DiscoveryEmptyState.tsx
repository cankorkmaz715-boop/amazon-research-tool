/** Step 239: Empty state when no discovery results. */
const wrapStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '2rem 1.5rem',
  marginBottom: '1rem',
  textAlign: 'center',
  color: '#666',
}

export default function DiscoveryEmptyState({ message = 'No discovery results. Try a different query or filter.' }: { message?: string }) {
  return (
    <div style={wrapStyle} aria-label="Discovery empty state">
      <p style={{ margin: 0 }}>{message}</p>
    </div>
  )
}
