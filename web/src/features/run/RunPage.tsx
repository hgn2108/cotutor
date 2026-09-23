import clsx from 'clsx'
import { ArrowLeft, BookOpen, Cog, RotateCw, Square } from 'lucide-react'
import { useState } from 'react'
import { type LearnMode, ModeToggle } from '../../components/ModeToggle'
import { Badge, Button, Card, difficultyTone } from '../../components/ui'
import type { RunState } from '../../lib/useRun'
import { SummaryBar } from '../hood/SummaryBar'
import { UnderTheHood } from '../hood/UnderTheHood'
import { Lesson } from '../lesson/Lesson'

interface Props {
  state: RunState
  runId: number
  mode: LearnMode
  setMode: (m: LearnMode) => void
  dark: boolean
  onSolve: (problem: string, fresh?: boolean) => void
  onCancel: () => void
  onBack: () => void
}

/** A single problem: the lesson, with the engineering view one click away. */
export function RunPage({ state, runId, mode, setMode, dark, onSolve, onCancel, onBack }: Props) {
  const [view, setView] = useState<'lesson' | 'hood'>('lesson')
  const guided = mode === 'guided'
  // In guided mode the pattern tags would give the answer away before the learner guesses.
  const tagsRevealed = !guided || view === 'hood'

  const viewButton = (id: 'lesson' | 'hood', label: string, Icon: typeof BookOpen) => (
    <button onClick={() => { setView(id); window.scrollTo({ top: 0 }) }}
      className={clsx('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium', view === id ? 'bg-sunken text-ink' : 'text-muted hover:text-ink')}>
      <Icon className="size-3.5" />{label}
    </button>
  )

  return (
    <main className="mx-auto max-w-[1320px] px-4 pb-20 pt-5 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button variant="ghost" onClick={onBack} className="-ml-2"><ArrowLeft className="size-4" />New problem</Button>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {view === 'lesson' && <ModeToggle mode={mode} setMode={setMode} size="sm" />}
          <div className="flex rounded-lg border border-line p-0.5">
            {viewButton('lesson', 'Lesson', BookOpen)}
            {viewButton('hood', 'Under the hood', Cog)}
          </div>
          {state.status === 'running' && <Button variant="outline" className="text-xs" onClick={onCancel}><Square className="size-3" />Stop</Button>}
          {state.status !== 'running' && state.problem && (
            <Button variant="outline" className="text-xs" onClick={() => onSolve(state.problem, true)} title="Run all agents again instead of replaying a saved run">
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
        <Lesson key={runId} state={state} guided={guided} dark={dark} onSolve={(p) => { setView('lesson'); onSolve(p) }}
          onUnderTheHood={() => { setView('hood'); window.scrollTo({ top: 0 }) }} />
      </div>
      {view === 'hood' && <UnderTheHood state={state} dark={dark} />}
    </main>
  )
}
