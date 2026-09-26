import clsx from 'clsx'
import { ArrowLeft, BookOpen, Cog, MapIcon, RotateCw, Square, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { type LearnMode, ModeToggle } from '../../components/ModeToggle'
import { Badge, Button, Card, difficultyTone } from '../../components/ui'
import type { RunState } from '../../lib/useRun'
import { SummaryBar } from '../hood/SummaryBar'
import { UnderTheHood } from '../hood/UnderTheHood'
import type { RoadmapLink } from '../lesson/context'
import { Lesson } from '../lesson/Lesson'

interface Props {
  state: RunState
  runId: number
  mode: LearnMode
  setMode: (m: LearnMode) => void
  dark: boolean
  onPractice: (title: string) => void
  onRetry: () => void
  onRegenerate: () => void
  onCancel: () => void
  onBack: () => void
  onBrowse: () => void
  roadmap?: RoadmapLink
  onComplete?: (score: number | null, mode: 'guided' | 'walkthrough') => void
  lessonKey: string
}

/** Turn a failure into something a learner can act on. The raw detail stays under the hood. */
export function friendlyError(error: NonNullable<RunState['error']>): { title: string; body: string; retry: boolean } {
  const m = error.message
  if (error.code === 'cancelled') return { title: 'You stopped this run.', body: 'Start it again whenever you like.', retry: true }
  if (error.code === 'overloaded' || error.code === 'rate_limited' || /overloaded|429|RESOURCE_EXHAUSTED/i.test(m)) {
    return {
      title: 'The AI tutor is out of capacity right now',
      body: 'New problems can’t be prepared at the moment. Problems marked ⚡ instant still work: try one from a roadmap or the examples on the home page, or add your own free Gemini key in Settings (⚙ at the top right).',
      retry: true,
    }
  }
  if (error.code === 'no_key') return { title: 'No AI key configured', body: m, retry: false }
  if (/connect|connection/i.test(m)) {
    return { title: 'Can’t reach the Cotutor server', body: 'The free server may be waking up (up to a minute). Try again shortly.', retry: true }
  }
  return { title: 'This lesson couldn’t be prepared', body: m, retry: error.code !== 'unsupported' && error.code !== 'unrecognized' }
}

/** A single problem: the lesson, with the engineering view one click away. */
export function RunPage(p: Props) {
  const { state, runId, mode, setMode, dark, roadmap } = p
  const [view, setView] = useState<'lesson' | 'hood'>('lesson')
  const scroll = useRef<Record<'lesson' | 'hood', number>>({ lesson: 0, hood: 0 })
  const guided = mode === 'guided'
  // In guided mode the pattern tags would give the answer away before the learner guesses.
  const tagsRevealed = !guided || view === 'hood'
  const running = state.status === 'running'
  const title = state.spec?.title ?? (running ? 'Reading the problem…' : firstLine(state.problem))

  useEffect(() => { setView('lesson') }, [runId])

  const switchTo = (id: 'lesson' | 'hood') => {
    if (id === view) return
    scroll.current[view] = window.scrollY
    setView(id)
    requestAnimationFrame(() => window.scrollTo({ top: scroll.current[id] }))
  }

  const viewButton = (id: 'lesson' | 'hood', label: string, Icon: typeof BookOpen) => (
    <button onClick={() => switchTo(id)} aria-pressed={view === id}
      className={clsx('flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium', view === id ? 'bg-sunken text-ink' : 'text-muted hover:text-ink')}>
      <Icon className="size-3.5" />{label}
    </button>
  )

  const regenerate = () => {
    if (window.confirm('Regenerate this lesson with AI? This runs every agent again (about a minute, and it uses AI quota). If it fails, the saved lesson is still available with "Try again".')) p.onRegenerate()
  }

  const err = state.error && friendlyError(state.error)

  return (
    <main className="mx-auto max-w-[1320px] px-4 pb-20 pt-5 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button variant="ghost" onClick={p.onBack} className="-ml-2"><ArrowLeft className="size-4" />{roadmap ? 'Roadmap' : 'Home'}</Button>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {view === 'lesson' && <ModeToggle mode={mode} setMode={setMode} size="sm" />}
          <div className="flex rounded-lg border border-line p-0.5">
            {viewButton('lesson', 'Lesson', BookOpen)}
            {viewButton('hood', 'Under the hood', Cog)}
          </div>
          {running && <Button variant="outline" className="text-xs" onClick={p.onCancel}><Square className="size-3" />Stop</Button>}
        </div>
      </div>

      {view === 'lesson' ? (
        <div className="mb-5 flex flex-wrap items-center gap-2">
          <h1 className="min-w-0 break-words text-[22px] font-semibold tracking-tight">{title}</h1>
          {state.spec && <Badge tone={difficultyTone[state.spec.difficulty]}>{state.spec.difficulty}</Badge>}
          {tagsRevealed && state.spec?.pattern_tags.map((t) => <Badge key={t}>{t}</Badge>)}
          {state.summary?.replayed && state.summary.recording === 'scripted' && (
            <Badge tone="accent" title="Agent responses are scripted for this offline demo; execution results are real.">Offline demo</Badge>
          )}
        </div>
      ) : (
        <div className="mb-5"><SummaryBar state={state} /></div>
      )}

      {err && (
        <Card className="mb-5 border-bad/30 bg-bad-soft/40 p-4">
          <div className="flex gap-3">
            <TriangleAlert className="mt-0.5 size-4 shrink-0 text-bad" />
            <div className="min-w-0 flex-1">
              <div className="text-[14px] font-medium">{err.title}</div>
              <p className="mt-0.5 text-[13px] leading-relaxed text-muted">{err.body}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {err.retry && <Button onClick={p.onRetry}><RotateCw className="size-3.5" />Try again</Button>}
                <Button variant="outline" onClick={p.onBrowse}><MapIcon className="size-3.5" />Browse instant problems</Button>
                {view === 'lesson' && <Button variant="ghost" className="text-xs" onClick={() => switchTo('hood')}>Technical details</Button>}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* The lesson stays mounted while peeking under the hood so progress isn't lost. */}
      <div className={view === 'lesson' ? '' : 'hidden'}>
        <Lesson key={runId} state={state} guided={guided} dark={dark} visible={view === 'lesson'}
          onPractice={p.onPractice} onUnderTheHood={() => switchTo('hood')} roadmap={roadmap}
          onComplete={p.onComplete} storageKey={p.lessonKey} />
      </div>
      {view === 'hood' && <UnderTheHood state={state} dark={dark} onRegenerate={running ? undefined : regenerate} />}
    </main>
  )
}

function firstLine(text: string): string {
  const line = text.trim().split('\n')[0].replace(/^LeetCode problem:\s*/i, '').replace(/\.\s*Solve and explain it\.?$/i, '')
  return line.length > 80 ? line.slice(0, 77) + '…' : line || 'Untitled problem'
}
