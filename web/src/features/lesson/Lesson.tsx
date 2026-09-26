import clsx from 'clsx'
import { BadgeCheck, Check, ChevronRight, CircleSlash, Lock, ShieldAlert } from 'lucide-react'
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Spinner } from '../../components/ui'
import type { RunState } from '../../lib/useRun'
import { BottleneckChapter } from './chapters/BottleneckChapter'
import { BruteForceChapter } from './chapters/BruteForceChapter'
import { ComplexityChapter } from './chapters/ComplexityChapter'
import { EdgeCasesChapter } from './chapters/EdgeCasesChapter'
import { InsightChapter } from './chapters/InsightChapter'
import { PatternChapter } from './chapters/PatternChapter'
import { ProblemChapter } from './chapters/ProblemChapter'
import { RecapChapter } from './chapters/RecapChapter'
import { WatchChapter } from './chapters/WatchChapter'
import { type ChapterId, LessonContext, type LessonCtx, type RoadmapLink, type Score } from './context'

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
  { id: 'brute', title: 'Start with brute force', blurb: 'The simplest correct idea, before any cleverness.', ready: (s) => !!s.lessonIntro, waiting: 'The coach is preparing this…', render: () => <BruteForceChapter /> },
  { id: 'bottleneck', title: 'Find the wasted work', blurb: 'Where does the brute force repeat itself?', ready: (s) => !!s.lessonIntro, waiting: 'The coach is preparing this…', render: () => <BottleneckChapter /> },
  { id: 'insight', title: 'The key insight', blurb: 'How the optimized solution removes that work.', ready: (s) => !!s.explanation && s.solutions.length > 0, waiting: 'Verifying the solution before explaining it…', render: () => <InsightChapter /> },
  { id: 'watch', title: 'Watch it run', blurb: 'Step through the real execution, predicting as you go.', ready: (s) => !!s.trace, waiting: 'Recording the execution…', render: () => <WatchChapter /> },
  { id: 'complexity', title: 'Why it’s that fast', blurb: 'Derive the Big-O from the code, then check it against real step counts.', ready: (s) => !!s.lessonDeep, waiting: 'Counting steps and deriving the complexity…', render: () => <ComplexityChapter /> },
  { id: 'edges', title: 'Test yourself', blurb: 'Predict the output on the inputs that trip people up.', ready: (s) => s.verifications.length > 0 && s.status !== 'running', waiting: 'Finishing verification…', render: () => <EdgeCasesChapter /> },
  { id: 'recap', title: 'Recap', blurb: 'The rule to remember, and where to practice it next.', ready: (s) => !!s.lessonDeep || s.status !== 'running', waiting: 'Wrapping up…', render: () => <RecapChapter /> },
]

interface Props {
  state: RunState
  guided: boolean
  dark: boolean
  visible: boolean
  onPractice: (title: string) => void
  onUnderTheHood: () => void
  roadmap?: RoadmapLink
  onComplete?: (score: number | null, mode: 'guided' | 'walkthrough') => void
  onDirty?: (dirty: boolean) => void
}

export function Lesson({ state, guided, dark, visible, onPractice, onUnderTheHood, roadmap, onComplete, onDirty }: Props) {
  const [done, setDone] = useState<Set<ChapterId>>(new Set())
  const [scores, setScores] = useState<Partial<Record<ChapterId, Score>>>({})
  const refs = useRef<Partial<Record<ChapterId, HTMLElement | null>>>({})
  const lastCompleted = useRef<ChapterId | null>(null)

  const record = useCallback((id: ChapterId, score: Score) => setScores((s) => ({ ...s, [id]: score })), [])
  const [finished, setFinished] = useState(false)
  const finish = useCallback((score: number | null) => {
    if (finished) return
    setFinished(true)
    onComplete?.(score, guided ? 'guided' : 'walkthrough')
  }, [finished, onComplete, guided])
  const complete = useCallback((id: ChapterId) => {
    lastCompleted.current = id
    setDone((d) => new Set(d).add(id))
  }, [])

  // A guided lesson is finished once every step is done; its score feeds spaced repetition.
  // Skipped questions count as misses, so skipping through never marks a problem learned.
  useEffect(() => {
    if (!guided || finished || !CHAPTERS.every((c) => done.has(c.id))) return
    const t = Object.values(scores).reduce((a, x) => ({ c: a.c + x.correct, n: a.n + x.total }), { c: 0, n: 0 })
    finish(t.n ? t.c / t.n : 0)
  }, [done, scores, guided, finished, finish])

  useEffect(() => { onDirty?.(guided && done.size > 0 && !finished) }, [guided, done, finished, onDirty])

  const ctx: LessonCtx = useMemo(() => ({
    state, guided, dark, visible, onPractice, scores, record, complete, isDone: (id) => done.has(id), roadmap, finish, finished,
  }), [state, guided, dark, visible, onPractice, scores, record, complete, done, roadmap, finish, finished])

  const runFinished = state.status !== 'running'
  const failed = state.status === 'error'
  const firstOpen = CHAPTERS.findIndex((c) => !done.has(c.id))
  const unlockedUpTo = guided ? (firstOpen === -1 ? CHAPTERS.length - 1 : firstOpen) : CHAPTERS.length - 1
  // A run that stopped early shows what it managed to prepare, then one explanation instead of empty steps.
  const firstMissing = CHAPTERS.findIndex((c) => !c.ready(state))
  const cutoff = failed && firstMissing >= 0 ? firstMissing : CHAPTERS.length
  const shown = CHAPTERS.slice(0, Math.min(unlockedUpTo + 1, cutoff))

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
  const currentIdx = guided ? unlockedUpTo : -1

  return (
    <LessonContext.Provider value={ctx}>
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[250px_minmax(0,1fr)] lg:gap-6">
        <aside className="min-w-0 lg:sticky lg:top-20 lg:self-start">
          <nav aria-label="Lesson steps" className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1 lg:mx-0 lg:grid lg:gap-0.5 lg:overflow-visible lg:p-0">
            {CHAPTERS.map((c, k) => {
              const unavailable = k >= cutoff
              const locked = k > unlockedUpTo || unavailable
              const isDone = done.has(c.id)
              const ready = c.ready(state)
              const current = k === currentIdx && !isDone && !unavailable
              return (
                <button key={c.id} disabled={locked} onClick={() => jump(c.id)} aria-current={current ? 'step' : undefined}
                  title={unavailable ? 'Not prepared: the run stopped early' : locked ? 'Finish the earlier steps to unlock' : c.title}
                  className={clsx('flex shrink-0 items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-[13px] transition',
                    current ? 'bg-accent-soft font-medium text-ink' : 'text-muted hover:bg-sunken hover:text-ink', locked && 'cursor-default opacity-45 hover:bg-transparent hover:text-muted')}>
                  <span className={clsx('flex size-5 shrink-0 items-center justify-center rounded-full text-[10.5px] font-semibold',
                    isDone ? 'bg-ok-soft text-ok' : current ? 'bg-accent text-white dark:text-[#0e0e13]' : 'bg-sunken text-faint')}>
                    {isDone ? <Check className="size-3" strokeWidth={3} /> : locked ? <Lock className="size-2.5" /> : k + 1}
                  </span>
                  <span className={clsx('flex-1 truncate', !current && 'hidden lg:inline')}>{c.title}</span>
                  {!ready && !runFinished && !locked && <Spinner className="hidden size-3 text-faint lg:inline-block" />}
                </button>
              )
            })}
          </nav>
          <button onClick={onUnderTheHood} className="mt-4 hidden w-full rounded-xl border border-line bg-panel p-3 text-left transition hover:border-accent/50 lg:block">
            <HoodStatus state={state} running={running.map((s) => s.label.split(':')[0])} />
            <span className="mt-1.5 flex items-center gap-0.5 text-[11.5px] font-medium text-accent">Under the hood <ChevronRight className="size-3" /></span>
          </button>
        </aside>

        <div className="grid min-w-0 gap-5">
          {shown.map((c, k) => {
            const ready = c.ready(state)
            return (
              <section key={c.id} ref={(el) => { refs.current[c.id] = el }} className="min-w-0 scroll-mt-20 rounded-2xl border border-line bg-panel p-4 sm:p-6">
                <header className="mb-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-accent">Step {k + 1} of {CHAPTERS.length}</div>
                  <h2 className="mt-0.5 text-[19px] font-semibold tracking-tight">{c.title}</h2>
                  <p className="mt-0.5 text-[13.5px] text-muted">{c.blurb}</p>
                </header>
                {ready ? c.render() : runFinished ? (
                  <Unavailable id={c.id} />
                ) : (
                  <div className="flex h-24 items-center justify-center gap-2 rounded-xl bg-sunken/60 text-sm text-faint"><Spinner />{c.waiting}</div>
                )}
              </section>
            )
          })}
          {failed && cutoff < CHAPTERS.length && (guided ? unlockedUpTo >= cutoff : true) && (
            <div className="rounded-2xl border border-dashed border-line p-5 text-center text-[13.5px] text-muted">
              The rest of this lesson couldn’t be prepared because the run stopped early. See the message above to try again.
            </div>
          )}
        </div>
      </div>
    </LessonContext.Provider>
  )
}

function HoodStatus({ state, running }: { state: RunState; running: string[] }) {
  if (state.status === 'error') {
    return (
      <>
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-muted"><CircleSlash className="size-4" />Run stopped</div>
        <p className="mt-1 text-[11.5px] leading-4 text-muted">It ended before the solution could be verified.</p>
      </>
    )
  }
  if (!state.summary) {
    return (
      <>
        <div className="flex items-center gap-2 text-[13px] font-medium"><Spinner className="size-3 text-accent" />Agents at work</div>
        <p className="mt-1 text-[11.5px] leading-4 text-muted">{running.length ? running.join(', ') : 'Starting…'}</p>
      </>
    )
  }
  const s = state.summary
  return (
    <>
      {s.verified
        ? <div className="flex items-center gap-1.5 text-[13px] font-medium text-ok"><BadgeCheck className="size-4" />Solution verified</div>
        : <div className="flex items-center gap-1.5 text-[13px] font-medium text-bad"><ShieldAlert className="size-4" />Not verified</div>}
      <p className="mt-1 text-[11.5px] leading-4 text-muted">{s.tests_passed ?? 0}/{s.tests_total ?? 0} tests passed · {s.stress_trials ?? 0} random inputs checked</p>
    </>
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
