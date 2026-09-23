import clsx from 'clsx'
import { BadgeCheck, Check, ChevronRight, Lock, ShieldAlert } from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RunState } from '../../lib/useRun'
import { Spinner } from '../ui'
import { BottleneckChapter, BruteChapter, PatternChapter, ProblemChapter } from './ChaptersStart'
import { ComplexityChapter, EdgesChapter, InsightChapter, RecapChapter, WatchChapter } from './ChaptersEnd'
import { type ChapterId, LessonContext, type LessonCtx, type Score } from './context'

interface ChapterDef {
  id: ChapterId
  title: string
  blurb: string
  ready: (s: RunState) => boolean
  waiting: string
  render: () => ReactNode
}

const CHAPTERS: ChapterDef[] = [
  { id: 'problem', title: 'Understand the problem', blurb: 'Pin down exactly what goes in and what comes out.', ready: (s) => !!s.spec, waiting: 'Reading the problem…', render: () => <ProblemChapter /> },
  { id: 'pattern', title: 'Spot the pattern', blurb: 'Which technique does the wording point to?', ready: (s) => !!s.lessonIntro, waiting: 'The coach is preparing this…', render: () => <PatternChapter /> },
  { id: 'brute', title: 'Start with brute force', blurb: 'The simplest correct idea, before any cleverness.', ready: (s) => !!s.lessonIntro, waiting: 'The coach is preparing this…', render: () => <BruteChapter /> },
  { id: 'bottleneck', title: 'Find the wasted work', blurb: 'Where does the brute force repeat itself?', ready: (s) => !!s.lessonIntro, waiting: 'The coach is preparing this…', render: () => <BottleneckChapter /> },
  { id: 'insight', title: 'The key insight', blurb: 'How the optimized solution removes that work.', ready: (s) => !!s.explanation && s.solutions.length > 0, waiting: 'Verifying the solution before explaining it…', render: () => <InsightChapter /> },
  { id: 'watch', title: 'Watch it run', blurb: 'Step through the real execution, predicting as you go.', ready: (s) => !!s.trace, waiting: 'Recording the execution…', render: () => <WatchChapter /> },
  { id: 'complexity', title: 'Why it’s that fast', blurb: 'Derive the Big-O from the code, then check it against real step counts.', ready: (s) => !!s.lessonDeep, waiting: 'Counting steps and deriving the complexity…', render: () => <ComplexityChapter /> },
  { id: 'edges', title: 'Test yourself', blurb: 'Predict the output on the inputs that trip people up.', ready: (s) => s.verifications.length > 0 && s.status !== 'running', waiting: 'Finishing verification…', render: () => <EdgesChapter /> },
  { id: 'recap', title: 'Recap', blurb: 'The rule to remember, and where to practice it next.', ready: (s) => !!s.lessonDeep || s.status !== 'running', waiting: 'Wrapping up…', render: () => <RecapChapter /> },
]

interface Props {
  state: RunState
  guided: boolean
  dark: boolean
  onSolve: (problem: string) => void
  onUnderTheHood: () => void
}

export function Lesson({ state, guided, dark, onSolve, onUnderTheHood }: Props) {
  const [done, setDone] = useState<Set<ChapterId>>(new Set())
  const [scores, setScores] = useState<Partial<Record<ChapterId, Score>>>({})
  const refs = useRef<Partial<Record<ChapterId, HTMLElement | null>>>({})
  const lastCompleted = useRef<ChapterId | null>(null)

  const complete = useCallback((id: ChapterId) => {
    lastCompleted.current = id
    setDone((d) => new Set(d).add(id))
  }, [])
  const record = useCallback((id: ChapterId, score: Score) => setScores((s) => ({ ...s, [id]: score })), [])
  const ctx: LessonCtx = useMemo(() => ({
    state, guided, dark, onSolve, scores, record, complete, isDone: (id) => done.has(id),
  }), [state, guided, dark, onSolve, scores, record, complete, done])

  const finished = state.status !== 'running'
  const firstOpen = CHAPTERS.findIndex((c) => !done.has(c.id))
  const unlockedUpTo = guided ? (firstOpen === -1 ? CHAPTERS.length - 1 : firstOpen) : CHAPTERS.length - 1
  const visible = CHAPTERS.slice(0, unlockedUpTo + 1)

  // After finishing a chapter, bring the next one into view.
  useEffect(() => {
    const id = lastCompleted.current
    if (!id) return
    const next = CHAPTERS[CHAPTERS.findIndex((c) => c.id === id) + 1]
    if (next) setTimeout(() => refs.current[next.id]?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60)
    lastCompleted.current = null
  }, [done])

  const jump = (id: ChapterId) => refs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  const running = state.stages.filter((s) => s.status === 'running')

  return (
    <LessonContext.Provider value={ctx}>
      <div className="grid gap-6 lg:grid-cols-[250px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-20 lg:self-start">
          <nav className="grid gap-0.5">
            {CHAPTERS.map((c, k) => {
              const locked = k > unlockedUpTo
              const isDone = done.has(c.id)
              const ready = c.ready(state)
              const current = guided && k === unlockedUpTo && !isDone
              return (
                <button key={c.id} disabled={locked} onClick={() => jump(c.id)}
                  className={clsx('flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition',
                    current ? 'bg-accent-soft font-medium text-ink' : 'text-muted hover:bg-sunken hover:text-ink', locked && 'cursor-default opacity-45 hover:bg-transparent hover:text-muted')}>
                  <span className={clsx('flex size-5 shrink-0 items-center justify-center rounded-full text-[10.5px] font-semibold',
                    isDone ? 'bg-ok-soft text-ok' : current ? 'bg-accent text-white dark:text-[#0e0e13]' : 'bg-sunken text-faint')}>
                    {isDone ? <Check className="size-3" strokeWidth={3} /> : locked ? <Lock className="size-2.5" /> : k + 1}
                  </span>
                  <span className="flex-1 truncate">{c.title}</span>
                  {!ready && !finished && !locked && <Spinner className="size-3 text-faint" />}
                </button>
              )
            })}
          </nav>
          <button onClick={onUnderTheHood} className="mt-4 w-full rounded-xl border border-line bg-panel p-3 text-left transition hover:border-accent/50">
            {state.summary ? (
              state.summary.verified
                ? <div className="flex items-center gap-1.5 text-[13px] font-medium text-ok"><BadgeCheck className="size-4" />Solution verified</div>
                : <div className="flex items-center gap-1.5 text-[13px] font-medium text-bad"><ShieldAlert className="size-4" />Not verified</div>
            ) : (
              <div className="flex items-center gap-2 text-[13px] font-medium"><Spinner className="size-3 text-accent" />Agents at work</div>
            )}
            <p className="mt-1 text-[11.5px] leading-4 text-muted">
              {state.summary
                ? `${state.summary.tests_passed ?? 0}/${state.summary.tests_total ?? 0} tests · ${state.summary.stress_trials ?? 0} random trials`
                : running.length ? running.map((s) => s.label.split(':')[0]).join(', ') : 'Starting…'}
            </p>
            <span className="mt-1.5 flex items-center gap-0.5 text-[11.5px] font-medium text-accent">Under the hood <ChevronRight className="size-3" /></span>
          </button>
        </aside>

        <div className="grid gap-5">
          {visible.map((c, k) => {
            const ready = c.ready(state)
            return (
              <section key={c.id} ref={(el) => { refs.current[c.id] = el }} className="scroll-mt-20 rounded-2xl border border-line bg-panel p-5 sm:p-6">
                <header className="mb-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-accent">Step {k + 1}</div>
                  <h2 className="mt-0.5 text-[19px] font-semibold tracking-tight">{c.title}</h2>
                  <p className="mt-0.5 text-[13.5px] text-muted">{c.blurb}</p>
                </header>
                {ready ? c.render() : finished ? (
                  <Unavailable id={c.id} />
                ) : (
                  <div className="flex h-24 items-center justify-center gap-2 rounded-xl bg-sunken/60 text-sm text-faint"><Spinner />{c.waiting}</div>
                )}
              </section>
            )
          })}
          {guided && firstOpen === -1 && (
            <p className="py-4 text-center text-sm text-muted">Lesson complete. Try a similar problem above to lock the pattern in.</p>
          )}
        </div>
      </div>
    </LessonContext.Provider>
  )
}

function Unavailable({ id }: { id: ChapterId }) {
  return (
    <LessonContext.Consumer>
      {(ctx) => (
        <div className="rounded-xl bg-sunken/60 p-4 text-sm text-muted">
          This part couldn't be generated for this run.
          {ctx?.guided && !ctx.isDone(id) && <button onClick={() => ctx.complete(id)} className="ml-2 font-medium text-accent hover:underline">Skip ahead</button>}
        </div>
      )}
    </LessonContext.Consumer>
  )
}
