import { useState } from 'react'

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

interface ToggleProps { on: boolean; onChange: (v: boolean) => void; label: string }

function Toggle({ on, onChange, label }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative inline-flex items-center w-11 h-6 rounded-full transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-violet-500/30 ${on ? 'bg-gradient-to-r from-violet-600 to-indigo-600 shadow-lg shadow-violet-500/20' : 'bg-white/10'}`}
    >
      <span
        className={`absolute w-4 h-4 rounded-full bg-white shadow-md transition-all duration-300 ${on ? 'translate-x-6' : 'translate-x-1'}`}
      />
    </button>
  )
}

interface SectionProps { title: string; icon: string; children: React.ReactNode }

function Section({ title, icon, children }: SectionProps) {
  return (
    <section className="glass rounded-2xl overflow-hidden mb-5 glow-indigo">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/[0.07] bg-white/[0.02]">
        <span className="text-lg">{icon}</span>
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">{title}</h3>
      </div>
      <div>{children}</div>
    </section>
  )
}

interface RowProps {
  label: string
  desc: string
  last?: boolean
  children: React.ReactNode
}

function Row({ label, desc, last, children }: RowProps) {
  return (
    <div className={`flex items-center justify-between px-5 py-4 gap-6 transition-colors duration-150 hover:bg-white/[0.02] ${!last ? 'border-b border-white/[0.05]' : ''}`}>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-slate-200">{label}</div>
        <div className="text-xs text-slate-500 mt-0.5">{desc}</div>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

function SavedFlash({ show }: { show: boolean }) {
  if (!show) return null
  return (
    <span className="ml-3 text-xs text-emerald-400 font-medium animate-fade-in">✓ Saved</span>
  )
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
    setTimeout(() => setSavedKey(null), 1800)
  }
  function handleToggle(key: string, setter: (v: boolean) => void, v: boolean) {
    setter(v); setPref(key, v ? 'true' : 'false'); flash(key)
  }
  function handleSelect(key: string, setter: (v: string) => void, v: string) {
    setter(v); setPref(key, v); flash(key)
  }
  function resetAll() {
    if (!confirm('Reset all settings to defaults?')) return
    setWalkthrough(true); setPref(PREF_WALKTHROUGH, 'true')
    setOnboarding(true); setPref(PREF_ONBOARDING, 'true')
    setDemoMode(false); setPref(PREF_DEMO, 'false')
    setDensity('comfortable'); setPref(PREF_DENSITY, 'comfortable')
    setMarket('DE'); setPref(PREF_MARKET, 'DE')
    setTheme('light'); setPref(PREF_THEME, 'light')
    flash('reset')
  }

  const selectCls = "bg-white/5 border border-white/10 text-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/30 transition-all cursor-pointer min-w-[150px]"

  return (
    <div className="max-w-xl animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-violet-500/25">
            ⚙
          </div>
          <h2 className="text-xl font-bold text-slate-100">Settings</h2>
        </div>
        <p className="text-sm text-slate-500 ml-11">Preferences stored locally in your browser</p>
      </div>

      {/* Product */}
      <Section title="Product" icon="🧭">
        <Row label="Walkthrough" desc='Show the product tour and "Take a tour" on the dashboard.'>
          <div className="flex items-center">
            <Toggle on={walkthrough} onChange={(v) => handleToggle(PREF_WALKTHROUGH, setWalkthrough, v)} label="Toggle walkthrough" />
            <SavedFlash show={savedKey === PREF_WALKTHROUGH} />
          </div>
        </Row>
        <Row label="Onboarding" desc="Show the getting-started checklist for new workspaces.">
          <div className="flex items-center">
            <Toggle on={onboarding} onChange={(v) => handleToggle(PREF_ONBOARDING, setOnboarding, v)} label="Toggle onboarding" />
            <SavedFlash show={savedKey === PREF_ONBOARDING} />
          </div>
        </Row>
        <Row label="Demo mode" desc="Show example data in empty workspaces." last>
          <div className="flex items-center">
            <Toggle on={demoMode} onChange={(v) => handleToggle(PREF_DEMO, setDemoMode, v)} label="Toggle demo mode" />
            <SavedFlash show={savedKey === PREF_DEMO} />
          </div>
        </Row>
      </Section>

      {/* Display */}
      <Section title="Display" icon="🎨">
        <Row label="Dashboard density" desc="Compact reduces spacing; comfortable uses more padding.">
          <div className="flex items-center">
            <select value={density} onChange={(e) => handleSelect(PREF_DENSITY, setDensity, e.target.value)} className={selectCls} aria-label="Density">
              <option value="comfortable" className="bg-slate-900">Comfortable</option>
              <option value="compact" className="bg-slate-900">Compact</option>
            </select>
            <SavedFlash show={savedKey === PREF_DENSITY} />
          </div>
        </Row>
        <Row label="Theme" desc="Visual theme for the dashboard." last>
          <div className="flex items-center">
            <select value={theme} onChange={(e) => handleSelect(PREF_THEME, setTheme, e.target.value)} className={selectCls} aria-label="Theme">
              <option value="light" className="bg-slate-900">Light</option>
              <option value="dark" className="bg-slate-900">Dark</option>
              <option value="system" className="bg-slate-900">System</option>
            </select>
            <SavedFlash show={savedKey === PREF_THEME} />
          </div>
        </Row>
      </Section>

      {/* Research */}
      <Section title="Research" icon="🔬">
        <Row label="Default market" desc="Primary marketplace for discovery and scraping." last>
          <div className="flex items-center">
            <select value={market} onChange={(e) => handleSelect(PREF_MARKET, setMarket, e.target.value)} className={selectCls} aria-label="Market">
              <option value="DE" className="bg-slate-900">🇩🇪 DE – Amazon.de</option>
              <option value="US" className="bg-slate-900">🇺🇸 US – Amazon.com</option>
              <option value="AU" className="bg-slate-900">🇦🇺 AU – Amazon.com.au</option>
              <option value="UK" className="bg-slate-900">🇬🇧 UK – Amazon.co.uk</option>
              <option value="FR" className="bg-slate-900">🇫🇷 FR – Amazon.fr</option>
              <option value="IT" className="bg-slate-900">🇮🇹 IT – Amazon.it</option>
              <option value="ES" className="bg-slate-900">🇪🇸 ES – Amazon.es</option>
            </select>
            <SavedFlash show={savedKey === PREF_MARKET} />
          </div>
        </Row>
      </Section>

      {/* About */}
      <Section title="About" icon="ℹ️">
        <Row label="Version" desc="Amazon Research Tool">
          <span className="text-sm font-mono text-slate-500 glass px-2 py-0.5 rounded">v1.0.0</span>
        </Row>
        <Row label="LLM Copilot" desc="AI-powered opportunity analysis engine.">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            claude-sonnet-4-6
          </span>
        </Row>
        <Row label="Multi-market scraper" desc="Concurrent DE/US/AU via ThreadPoolExecutor.">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Active
          </span>
        </Row>
        <Row label="Reset all settings" desc="Restore all preferences to their defaults." last>
          <button
            type="button"
            onClick={resetAll}
            className="px-4 py-1.5 rounded-lg border border-red-500/30 text-red-400 text-sm font-medium hover:bg-red-500/10 transition-all duration-200 hover:border-red-500/50"
          >
            Reset
          </button>
        </Row>
      </Section>

      {savedKey === 'reset' && (
        <div className="glass rounded-xl p-3 border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm animate-fade-in">
          ✓ All settings reset to defaults.
        </div>
      )}
    </div>
  )
}
