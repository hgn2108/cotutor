import { useCallback, useEffect, useState } from 'react'
import { Header } from './components/Header'
import type { LearnMode } from './components/ModeToggle'
import { Home } from './features/home/Home'
import { RunPage } from './features/run/RunPage'
import { usePref, useTheme } from './lib/prefs'
import { useRun } from './lib/useRun'
import { sandbox, type SandboxStatus } from './sandbox/sandbox'

export default function App() {
  const { theme, setTheme, dark } = useTheme()
  const [apiKey, setApiKey] = usePref('cotutor.geminiKey', '')
  const [mode, setMode] = usePref('cotutor.mode', 'guided') as [LearnMode, (m: LearnMode) => void]
  const { state, features, connected, solve, cancel, reset } = useRun()
  const [sandboxStatus, setSandboxStatus] = useState<SandboxStatus>('cold')
  const [runId, setRunId] = useState(0)
  useEffect(() => sandbox.onStatus(setSandboxStatus), [])

  const start = useCallback((problem: string, fresh = false) => {
    setRunId((n) => n + 1) // remounts the lesson so progress starts fresh
    window.scrollTo({ top: 0 })
    void solve(problem, { apiKey: apiKey || undefined, fresh })
  }, [solve, apiKey])

  return (
    <div className="min-h-full">
      <Header
        sandboxStatus={sandboxStatus} connected={connected} features={features} theme={theme} setTheme={setTheme}
        apiKey={apiKey} setApiKey={setApiKey} onHome={reset}
      />
      {state.status === 'idle'
        ? <Home mode={mode} setMode={setMode} onSolve={start} />
        : <RunPage state={state} runId={runId} mode={mode} setMode={setMode} dark={dark} onSolve={start} onCancel={cancel} onBack={reset} />}
    </div>
  )
}
