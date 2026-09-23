import clsx from 'clsx'
import { ArrowLeft, BookOpen, Code2, Cog, FlaskConical, Gauge, RotateCw, Square } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Header } from './components/Header'
import { type LearnMode, ModeToggle } from './components/ModeToggle'
import { Home } from './components/Home'
import { Lesson } from './components/lesson/Lesson'
import { SummaryBar } from './components/SummaryBar'
import { CodeTab } from './components/tabs/CodeTab'
import { ComplexityTab } from './components/tabs/ComplexityTab'
import { TestsTab } from './components/tabs/TestsTab'
import { Timeline } from './components/Timeline'
import { Badge, Button, Card, difficultyTone } from './components/ui'
import { usePref, useTheme } from './lib/prefs'
import { useRun } from './lib/useRun'
import { sandbox, type SandboxStatus } from './sandbox/sandbox'

const HOOD_TABS = [
  { id: 'tests', label: 'Verification', icon: FlaskConical },
  { id: 'code', label: 'Code & fixes', icon: Code2 },
  { id: 'complexity', label: 'Timing at scale', icon: Gauge },
] as const
type HoodTab = (typeof HOOD_TABS)[number]['id']

export default function App() {
  const { theme, setTheme, dark } = useTheme()
  const [apiKey, setApiKey] = usePref('cotutor.geminiKey', '')
  const [solver, setSolver] = usePref('cotutor.solver', 'gemini') as ['gemini' | 'llama', (s: 'gemini' | 'llama') => void]
  const [mode, setMode] = usePref('cotutor.mode', 'guided') as [LearnMode, (m: LearnMode) => void]
  const { state, features, connected, solve, cancel, reset } = useRun()
  const [sandboxStatus, setSandboxStatus] = useState<SandboxStatus>('cold')
  const [view, setView] = useState<'lesson' | 'hood'>('lesson')
  const [hoodTab, setHoodTab] = useState<HoodTab>('tests')
  const [runId, setRunId] = useState(0)
  useEffect(() => sandbox.onStatus(setSandboxStatus), [])

  const start = useCallback((problem: string, fresh = false) => {
    setView('lesson')
    setRunId((n) => n + 1)
    window.scrollTo({ top: 0 })
    void solve(problem, { solver, apiKey: apiKey || undefined, fresh })
  }, [solve, solver, apiKey])

  const guided = mode === 'guided'
  // In guided mode the pattern tags would give the answer away before the learner guesses.
  const tagsRevealed = !guided || view === 'hood'

  return (
    <div className="min-h-full">
      <Header
        sandboxStatus={sandboxStatus} connected={connected} features={features} theme={theme} setTheme={setTheme}
        apiKey={apiKey} setApiKey={setApiKey} onHome={reset}
      />
      {state.status === 'idle' ? (
        <Home features={features} solver={solver} setSolver={setSolver} mode={mode} setMode={setMode} onSolve={(p) => start(p)} />
      ) : (
        <main className="mx-auto max-w-[1320px] px-4 pb-20 pt-5 sm:px-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Button variant="ghost" onClick={reset} className="-ml-2"><ArrowLeft className="size-4" />New problem</Button>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              {view === 'lesson' && <ModeToggle mode={mode} setMode={setMode} size="sm" />}
              <div className="flex rounded-lg border border-line p-0.5">
                <button onClick={() => setView('lesson')} className={clsx('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium', view === 'lesson' ? 'bg-sunken text-ink' : 'text-muted hover:text-ink')}><BookOpen className="size-3.5" />Lesson</button>
                <button onClick={() => setView('hood')} className={clsx('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium', view === 'hood' ? 'bg-sunken text-ink' : 'text-muted hover:text-ink')}><Cog className="size-3.5" />Under the hood</button>
              </div>
              {state.status === 'running' && <Button variant="outline" className="text-xs" onClick={cancel}><Square className="size-3" />Stop</Button>}
              {state.status !== 'running' && state.problem && (
                <Button variant="outline" className="text-xs" onClick={() => start(state.problem, true)} title="Run all agents again instead of replaying a saved run">
                  <RotateCw className="size-3" />Re-run live
                </Button>
              )}
            </div>
          </div>

          {view === 'lesson' ? (
            <div className="mb-5 flex flex-wrap items-center gap-2">
              <h1 className="text-[22px] font-semibold tracking-tight">{state.spec?.title ?? 'Reading the problem…'}</h1>
              {state.spec && <Badge tone={difficultyTone[state.spec.difficulty]}>{state.spec.difficulty}</Badge>}
              {tagsRevealed && state.spec?.pattern_tags.map((t) => <Badge key={t}>{t}</Badge>)}
              {state.summary?.replayed && state.summary.recording === 'scripted' && (
                <Badge tone="accent" title="Agent responses are scripted for this offline demo; execution results are real.">Offline demo</Badge>
              )}
            </div>
          ) : (
            <div className="mb-5"><SummaryBar state={state} /></div>
          )}

          {state.error && (
            <Card className="mb-5 border-bad/40 bg-bad-soft/40 p-4 text-sm"><span className="font-medium text-bad">{state.error.message}</span></Card>
          )}

          {/* The lesson stays mounted while peeking under the hood so progress isn't lost. */}
          <div className={view === 'lesson' ? '' : 'hidden'}>
            <Lesson key={runId} state={state} guided={guided} dark={dark} onSolve={start} onUnderTheHood={() => { setView('hood'); window.scrollTo({ top: 0 }) }} />
          </div>
          {view === 'hood' && (
            <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
              <aside className="lg:sticky lg:top-20 lg:self-start">
                <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Agent activity</div>
                <Timeline stages={state.stages} execLog={state.execLog} running={state.status === 'running'} />
                {state.summary && (
                  <p className="mt-3 font-mono text-[10.5px] leading-4 text-faint">
                    {state.summary.llm_calls} LLM calls · {(state.summary.input_tokens + state.summary.output_tokens).toLocaleString()} tokens · {(state.summary.ms / 1000).toFixed(1)}s
                  </p>
                )}
              </aside>
              <section className="min-w-0">
                <nav className="mb-4 flex gap-1 overflow-x-auto border-b border-line">
                  {HOOD_TABS.map(({ id, label, icon: Icon }) => (
                    <button key={id} onClick={() => setHoodTab(id)}
                      className={clsx('-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-[13px] font-medium transition',
                        hoodTab === id ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink')}>
                      <Icon className="size-4" />{label}
                    </button>
                  ))}
                </nav>
                {hoodTab === 'tests' && <TestsTab state={state} />}
                {hoodTab === 'code' && <CodeTab state={state} dark={dark} />}
                {hoodTab === 'complexity' && <ComplexityTab state={state} />}
              </section>
            </div>
          )}
        </main>
      )}
    </div>
  )
}
