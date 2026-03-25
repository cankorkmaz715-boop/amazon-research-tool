/** Step 239: Loading state for discovery search. */
const wrapStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e0e0e0',
  borderRadius: 8,
  padding: '1.5rem',
  marginBottom: '1rem',
}

export default function DiscoveryLoadingState() {
  return (
    <div style={wrapStyle} aria-busy aria-label="Loading discovery results">
      <p style={{ margin: 0, color: '#666' }}>Loading discovery results…</p>
    </div>
  )
}
