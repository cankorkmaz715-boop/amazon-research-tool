import { useState } from 'react'

// localStorage keys
const PREF_WALKTHROUGH = 'pref_walkthrough_enabled'
const PREF_ONBOARDING = 'pref_onboarding_enabled'
const PREF_DEMO = 'pref_demo_mode'
const PREF_DENSITY = 'pref_dashboard_density'
const PREF_MARKET = 'pref_default_market'
const PREF_THEME = 'pref_theme'

function getPref(key: string, fallback: string): string {
  try { return localStorage.getItem(key) ?? fallback } catch { return fallback }
}
function setPref(key: string, value: string) {
  try { localStorage.setItem(key, value) } catch {}
}

const S = {
  section: {
    marginBottom: '1.5rem',
    border: '1px solid #ddd',
    borderRadius: 6,
    overflow: 'hidden' as const,
    background: '#fff',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
  },
  sectionTitle: {
    padding: '0.75rem 1rem',
    fontWeight: 600,
    fontSize: '0.95rem',
    borderBottom: '1px solid #ddd',
    background: '#fafafa',
    margin: 0,
  },
  row: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '0.75rem 1rem',
    borderBottom: '1px solid #eee',
    gap: '0.75rem',
  },
  rowLast: {
    display: 'flex' as const,
    flexWrap: 'wrap' as const,
    alignItems: 'center' as const,
    justifyContent: 'space-between' as const,
    padding: '0.75rem 1rem',
    gap: '0.75rem',
  },
  label: { fontWeight: 500, fontSize: '0.9rem' },
  desc: { fontSize: '0.8rem', color: '#888', marginTop: '0.15rem' },
  select: {
    padding: '0.35rem 0.5rem',
    borderRadius: 4,
    border: '1px solid #ccc',
    fontSize: '0.875rem',
    minWidth: 130,
  },
  saved: { fontSize: '0.8rem', color: '#155724', marginLeft: '0.5rem' },
}

interface ToggleProps {
  on: boolean
  onChange: (v: boolean) => void
  label: string
}

function Toggle({ on, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      aria-pressed={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      style={{
        width: '2.5rem',
        height: '1.25rem',
        borderRadius: 999,
        background: on ? '#0063cc' : '#ccc',
        border: 'none',
        cursor: 'pointer',
        position: 'relative',
        flexShrink: 0,
        transition: 'background 0.15s',
        padding: 0,
      }}
    >
      <span
        style={{
          position: 'absolute',
          width: '1rem',
          height: '1rem',
          borderRadius: '50%',
          background: '#fff',
          top: '0.125rem',
          left: on ? '1.25rem' : '0.125rem',
          transition: 'left 0.15s',
          boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
        }}
      />
    </button>
  )
}

function SavedIndicator({ show }: { show: boolean }) {
  if (!show) return null
  return <span style={S.saved}>✓ Saved</span>
}

export default function SettingsPage() {
  const [walkthrough, setWalkthrough] = useState(() => getPref(PREF_WALKTHROUGH, 'true') === 'true')
  const [onboarding, setOnboarding] = useState(() => getPref(PREF_ONBOARDING, 'true') === 'true')
  const [demoMode, setDemoMode] = useState(() => getPref(PREF_DEMO, 'false') === 'true')
  const [density, setDensity] = useState(() => getPref(PREF_DENSITY, 'comfortable'))
  const [market, setMarket] = useState(() => getPref(PREF_MARKET, 'DE'))
  const [theme, setTheme] = useState(() => getPref(PREF_THEME, 'light'))
  const [savedKey, setSavedKey] = useState<string | null>(null)

  function flash(key: string) {
    setSavedKey(key)
    setTimeout(() => setSavedKey(null), 1500)
  }

  function handleToggle(key: string, setter: (v: boolean) => void, v: boolean) {
    setter(v)
    setPref(key, v ? 'true' : 'false')
    flash(key)
  }

  function handleSelect(key: string, setter: (v: string) => void, v: string) {
    setter(v)
    setPref(key, v)
    flash(key)
  }

  // Reset all settings
  function resetAll() {
    if (!window.confirm('Reset all settings to defaults?')) return
    setWalkthrough(true); setPref(PREF_WALKTHROUGH, 'true')
    setOnboarding(true); setPref(PREF_ONBOARDING, 'true')
    setDemoMode(false); setPref(PREF_DEMO, 'false')
    setDensity('comfortable'); setPref(PREF_DENSITY, 'comfortable')
    setMarket('DE'); setPref(PREF_MARKET, 'DE')
    setTheme('light'); setPref(PREF_THEME, 'light')
    flash('reset')
  }

  return (
    <div style={{ maxWidth: 680 }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.25rem' }}>Settings</h2>
        <p style={{ margin: 0, color: '#666', fontSize: '0.875rem' }}>
          Product and display preferences — stored locally in your browser.
        </p>
      </div>

      {/* Product section */}
      <section style={S.section} aria-labelledby="section-product">
        <h3 id="section-product" style={S.sectionTitle}>Product</h3>

        <div style={S.row}>
          <div>
            <div style={S.label}>Walkthrough</div>
            <div style={S.desc}>Show the product tour and "Take a tour" on the dashboard.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Toggle on={walkthrough} onChange={(v) => handleToggle(PREF_WALKTHROUGH, setWalkthrough, v)} label="Toggle walkthrough" />
            <SavedIndicator show={savedKey === PREF_WALKTHROUGH} />
          </div>
        </div>

        <div style={S.row}>
          <div>
            <div style={S.label}>Onboarding</div>
            <div style={S.desc}>Show the getting-started checklist for new workspaces.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Toggle on={onboarding} onChange={(v) => handleToggle(PREF_ONBOARDING, setOnboarding, v)} label="Toggle onboarding" />
            <SavedIndicator show={savedKey === PREF_ONBOARDING} />
          </div>
        </div>

        <div style={S.rowLast}>
          <div>
            <div style={S.label}>Demo mode</div>
            <div style={S.desc}>Show example data in empty workspaces.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Toggle on={demoMode} onChange={(v) => handleToggle(PREF_DEMO, setDemoMode, v)} label="Toggle demo mode" />
            <SavedIndicator show={savedKey === PREF_DEMO} />
          </div>
        </div>
      </section>

      {/* Display section */}
      <section style={S.section} aria-labelledby="section-display">
        <h3 id="section-display" style={S.sectionTitle}>Display</h3>

        <div style={S.row}>
          <div>
            <div style={S.label}>Dashboard density</div>
            <div style={S.desc}>Compact reduces spacing; comfortable uses more padding.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <select
              style={S.select}
              value={density}
              onChange={(e) => handleSelect(PREF_DENSITY, setDensity, e.target.value)}
              aria-label="Dashboard density"
            >
              <option value="comfortable">Comfortable</option>
              <option value="compact">Compact</option>
            </select>
            <SavedIndicator show={savedKey === PREF_DENSITY} />
          </div>
        </div>

        <div style={S.rowLast}>
          <div>
            <div style={S.label}>Theme</div>
            <div style={S.desc}>Visual theme for the dashboard.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <select
              style={S.select}
              value={theme}
              onChange={(e) => handleSelect(PREF_THEME, setTheme, e.target.value)}
              aria-label="Theme"
            >
              <option value="light">Light</option>
              <option value="dark">Dark (coming soon)</option>
            </select>
            <SavedIndicator show={savedKey === PREF_THEME} />
          </div>
        </div>
      </section>

      {/* Research section */}
      <section style={S.section} aria-labelledby="section-research">
        <h3 id="section-research" style={S.sectionTitle}>Research</h3>

        <div style={S.rowLast}>
          <div>
            <div style={S.label}>Default market</div>
            <div style={S.desc}>Primary marketplace for discovery and scraping.</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <select
              style={S.select}
              value={market}
              onChange={(e) => handleSelect(PREF_MARKET, setMarket, e.target.value)}
              aria-label="Default market"
            >
              <option value="DE">DE – Amazon.de</option>
              <option value="US">US – Amazon.com</option>
              <option value="AU">AU – Amazon.com.au</option>
              <option value="UK">UK – Amazon.co.uk</option>
              <option value="FR">FR – Amazon.fr</option>
              <option value="IT">IT – Amazon.it</option>
              <option value="ES">ES – Amazon.es</option>
            </select>
            <SavedIndicator show={savedKey === PREF_MARKET} />
          </div>
        </div>
      </section>

      {/* About section */}
      <section style={S.section} aria-labelledby="section-about">
        <h3 id="section-about" style={S.sectionTitle}>About</h3>
        <div style={S.row}>
          <div>
            <div style={S.label}>Version</div>
            <div style={S.desc}>Amazon Research Tool</div>
          </div>
          <span style={{ fontSize: '0.875rem', color: '#888', fontFamily: 'monospace' }}>v1.0.0</span>
        </div>
        <div style={S.row}>
          <div>
            <div style={S.label}>LLM Copilot</div>
            <div style={S.desc}>Powered by claude-sonnet-4-6 with adaptive thinking.</div>
          </div>
          <span style={{ fontSize: '0.8rem', padding: '0.15rem 0.45rem', borderRadius: 4, background: '#d4edda', color: '#155724', fontWeight: 600 }}>Active</span>
        </div>
        <div style={S.rowLast}>
          <div>
            <div style={S.label}>Reset all settings</div>
            <div style={S.desc}>Restore all preferences to their defaults.</div>
          </div>
          <button
            type="button"
            style={{ padding: '0.3rem 0.75rem', fontSize: '0.875rem', cursor: 'pointer', borderRadius: 4, border: '1px solid #dc3545', color: '#dc3545', background: '#fff' }}
            onClick={resetAll}
          >
            Reset
          </button>
        </div>
      </section>

      {savedKey === 'reset' && (
        <div style={{ color: '#155724', background: '#d4edda', padding: '0.5rem 1rem', borderRadius: 4, fontSize: '0.875rem' }}>
          Settings reset to defaults.
        </div>
      )}
    </div>
  )
}
