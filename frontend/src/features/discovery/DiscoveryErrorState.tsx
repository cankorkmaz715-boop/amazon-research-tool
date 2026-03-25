/** Step 239: Error state for discovery search. */
const wrapStyle: React.CSSProperties = {
  background: '#fef2f2',
  border: '1px solid #fecaca',
  borderRadius: 8,
  padding: '1rem 1.25rem',
  marginBottom: '1rem',
  color: '#b91c1c',
}

export default function DiscoveryErrorState({ message }: { message: string }) {
  return (
    <div style={wrapStyle} role="alert" aria-label="Discovery error">
      <p style={{ margin: 0 }}>{message}</p>
    </div>
  )
}
