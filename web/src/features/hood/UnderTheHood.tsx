import clsx from 'clsx'
import { Code2, FlaskConical, Gauge } from 'lucide-react'
import { useState } from 'react'
import type { RunState } from '../../lib/useRun'
import { CodeTab } from './CodeTab'
import { Timeline } from './Timeline'
import { TimingTab } from './TimingTab'
import { VerificationTab } from './VerificationTab'

const TABS = [
  { id: 'tests', label: 'Verification', icon: FlaskConical },
  { id: 'code', label: 'Code & fixes', icon: Code2 },
  { id: 'timing', label: 'Timing at scale', icon: Gauge },
] as const
type TabId = (typeof TABS)[number]['id']

/** The engineering view: what the agents did, how the solution was verified, and at what cost. */
export function UnderTheHood({ state, dark }: { state: RunState; dark: boolean }) {
  const [tab, setTab] = useState<TabId>('tests')
  return (
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
          {TABS.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className={clsx('-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-[13px] font-medium transition',
                tab === id ? 'border-accent text-ink' : 'border-transparent text-muted hover:text-ink')}>
              <Icon className="size-4" />{label}
            </button>
          ))}
        </nav>
        {tab === 'tests' && <VerificationTab state={state} />}
        {tab === 'code' && <CodeTab state={state} dark={dark} />}
        {tab === 'timing' && <TimingTab state={state} />}
      </section>
    </div>
  )
}
