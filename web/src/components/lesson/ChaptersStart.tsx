import clsx from 'clsx'
import { Check, Lightbulb, Search, X } from 'lucide-react'
import { type ReactNode, useMemo, useState } from 'react'
import type { LineCountRun } from '../../lib/types'
import { Badge, Button } from '../ui'
import { CodeView, type LineMark } from '../viz/CodeView'
import { seededShuffle } from './answers'
import { useLesson } from './context'
import { ArgsInline, Callout, ContinueBar, HighlightedText, Prose, ThinkFirst } from './parts'

export function ProblemChapter() {
  const { state, guided, isDone } = useLesson()
  const { spec, lessonIntro } = state
  const showSignals = !!lessonIntro && (!guided || isDone('pattern'))
  return (
    <div>
      <div className="whitespace-pre-wrap rounded-xl border border-line bg-sunken/60 px-4 py-3.5 text-[14px] leading-relaxed">
        <HighlightedText text={state.problem} phrases={showSignals ? lessonIntro.signals.map((s) => s.phrase) : []} />
      </div>
      {spec && (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">In other words</div>
            <Prose>{spec.summary}</Prose>
            {spec.constraints.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">{spec.constraints.map((c) => <Badge key={c} className="font-mono">{c}</Badge>)}</div>
            )}
          </div>
          <div>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Examples</div>
            <div className="grid gap-1.5">
              {spec.examples.map((ex, k) => {
                let args: unknown[] = []
                try { args = JSON.parse(ex.args_json) } catch { /* shown raw below */ }
                return (
                  <div key={k} className="rounded-lg border border-line bg-panel px-3 py-2">
                    {args.length ? <ArgsInline args={args as never} spec={spec} /> : <span className="font-mono text-[12.5px]">{ex.args_json}</span>}
                    <span className="mx-2 text-faint">→</span>
                    <span className="font-mono text-[12.5px] font-semibold">{ex.expected_json}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
      {guided && (
        <Callout className="mt-4" icon={<Search className="size-4" />}>
          Before moving on, say it in your own words: what goes in, and what exactly must come out? Trace one example by hand.
        </Callout>
      )}
      <ContinueBar id="problem" enabled label="I understand the problem" />
    </div>
  )
}

export function PatternChapter() {
  const { state, guided, isDone, record } = useLesson()
  const intro = state.lessonIntro!
  const options = useMemo(() => seededShuffle(intro.pattern_options, state.problem), [intro, state.problem])
  const [picked, setPicked] = useState<string[]>([])
  const [revealed, setRevealed] = useState(false)
  const solved = picked.some((p) => options.find((o) => o.name === p)?.correct)
  const open = !guided || solved || revealed || isDone('pattern')

  const pick = (name: string) => {
    if (open || picked.includes(name)) return
    const next = [...picked, name]
    setPicked(next)
    if (options.find((o) => o.name === name)?.correct) record('pattern', { correct: next.length === 1 ? 1 : 0, total: 1 })
  }

  return (
    <div>
      <Prose className="mb-3 font-medium">Which technique fits this problem best?</Prose>
      <div className="grid gap-2 sm:grid-cols-2">
        {options.map((o) => {
          const chosen = picked.includes(o.name)
          const showFeedback = chosen || (open && (o.correct || !guided))
          return (
            <button
              key={o.name} onClick={() => pick(o.name)} disabled={open || chosen}
              className={clsx('rounded-xl border p-3.5 text-left transition',
                !open && !chosen && 'border-line bg-panel hover:border-accent/60 hover:shadow-sm',
                (chosen || open) && o.correct && 'border-ok/60 bg-ok-soft/60',
                chosen && !o.correct && 'border-bad/50 bg-bad-soft/50',
                open && !o.correct && !chosen && 'border-line bg-panel opacity-75')}
            >
              <div className="flex items-center gap-2 text-[14px] font-medium">
                {(chosen || open) && o.correct && <Check className="size-4 text-ok" strokeWidth={2.5} />}
                {chosen && !o.correct && <X className="size-4 text-bad" strokeWidth={2.5} />}
                {o.name}
              </div>
              {showFeedback && <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted">{o.feedback}</p>}
            </button>
          )
        })}
      </div>
      {guided && !open && (
        <div className="mt-3 flex items-center gap-3 text-xs text-faint">
          {picked.length > 0 && <span>Not that one. Read why, then try again.</span>}
          <button onClick={() => setRevealed(true)} className="underline-offset-2 hover:text-muted hover:underline">Show me the answer</button>
        </div>
      )}
      {open && (
        <div className="mt-5 grid gap-4">
          <Callout icon={<Lightbulb className="size-4" />} title={intro.pattern}>{intro.pattern_summary}</Callout>
          <div>
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">What in the wording gives it away</div>
            <ul className="grid gap-2">
              {intro.signals.map((s) => (
                <li key={s.phrase} className="flex flex-wrap items-baseline gap-x-2 text-[13.5px]">
                  <mark className="rounded bg-viz-3/25 px-1 font-medium text-ink">“{s.phrase}”</mark>
                  <span className="text-muted">{s.hint}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
      <ContinueBar id="pattern" enabled={open} />
    </div>
  )
}

export function BruteChapter() {
  const { state } = useLesson()
  const intro = state.lessonIntro!
  const [revealed, setRevealed] = useState(false)
  return (
    <div>
      <ThinkFirst
        prompt="Forget efficiency. What's the most direct way to get the right answer?"
        placeholder="e.g. check every possible…" revealLabel="Show the brute force"
        revealed={revealed} onReveal={() => setRevealed(true)}
      >
        <Prose>{intro.brute_force_idea}</Prose>
        <div className="mt-3"><CodeView code={intro.brute_force_code} maxHeight={360} /></div>
        <div className="mt-3 flex flex-wrap items-baseline gap-2 text-[13.5px]">
          <Badge tone="warn" className="font-mono text-[12px]">{intro.brute_force_time}</Badge>
          <span className="text-muted">{intro.brute_force_why}</span>
        </div>
        {intro.brute_is_optimal && (
          <Callout tone="ok" className="mt-3" icon={<Check className="size-4" />}>
            Measured: for this problem the direct approach already grows as slowly as it can. Sometimes the obvious solution is the optimal one, and the skill is recognizing that.
          </Callout>
        )}
        {state.oracle && !state.oracle.trusted && (
          <p className="mt-2 text-xs text-warn">Heads up: this brute force disagreed with one of the examples during verification, so treat it as a sketch.</p>
        )}
      </ThinkFirst>
      <ContinueBar id="brute" enabled={revealed} />
    </div>
  )
}

/** Per-line run counts for one input size, as heat + gutter badges. */
export function useLineHeat(runs: LineCountRun[] | undefined, n: number | null) {
  const run = runs?.find((r) => r.n === n) ?? runs?.at(-1)
  if (!run) return { run: undefined, heat: undefined, gutter: undefined }
  const max = Math.max(1, ...Object.values(run.counts))
  const heat: Record<number, number> = {}
  const gutter: Record<number, ReactNode> = {}
  for (const [line, c] of Object.entries(run.counts)) {
    heat[+line] = c / max
    gutter[+line] = <span className="rounded bg-panel/80 px-1.5 font-mono text-[11px] tabular-nums text-muted">×{c.toLocaleString()}</span>
  }
  return { run, heat, gutter }
}

export function SizePicker({ runs, n, setN }: { runs: LineCountRun[]; n: number | null; setN: (n: number) => void }) {
  const current = n ?? runs.at(-1)?.n
  return (
    <div className="flex items-center gap-2 text-xs text-muted">
      <span>input size n =</span>
      <div className="flex rounded-lg bg-sunken p-0.5">
        {runs.map((r) => (
          <button key={r.n} onClick={() => setN(r.n)} className={clsx('rounded-md px-2 py-0.5 font-mono', current === r.n ? 'bg-panel text-ink shadow-sm' : '')}>{r.n}</button>
        ))}
      </div>
    </div>
  )
}

export function BottleneckChapter() {
  const { state, guided, record } = useLesson()
  const intro = state.lessonIntro!
  const target = intro.bottleneck_line
  const [wrong, setWrong] = useState<number[]>([])
  const [hints, setHints] = useState(0)
  const [solved, setSolved] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const [n, setN] = useState<number | null>(null)
  const open = !guided || solved || revealed || target === null
  const brute = state.lineCounts?.brute_force
  const { run, heat, gutter } = useLineHeat(brute, n)

  const click = (line: number) => {
    if (open) return
    if (line === target) {
      setSolved(true)
      record('bottleneck', { correct: wrong.length === 0 ? 1 : 0, total: 1 })
    } else if (!wrong.includes(line)) {
      setWrong([...wrong, line])
      setHints((h) => Math.min(intro.bottleneck_hints.length, h + 1))
    }
  }
  const marks: Record<number, LineMark> = {}
  wrong.forEach((l) => { marks[l] = 'wrong' })
  if (open && target) marks[target] = 'correct'

  return (
    <div>
      {!open && <Prose className="mb-3 font-medium">Click the line that does the most repeated, wasted work as the input grows.</Prose>}
      {intro.brute_is_optimal && <Prose className="mb-3 font-medium">There's no wasted work to find here. Here's why the direct approach can't be beaten.</Prose>}
      <CodeView
        code={intro.brute_force_code} maxHeight={360} marks={marks}
        onLineClick={open ? undefined : click}
        heat={open ? heat : undefined} gutter={open ? gutter : undefined}
      />
      {!open && (
        <div className="mt-3 grid gap-2">
          {intro.bottleneck_hints.slice(0, hints).map((h, k) => (
            <Callout key={k} tone="warn" icon={<Lightbulb className="size-4" />}><span className="font-medium">Hint {k + 1}. </span>{h}</Callout>
          ))}
          <div className="flex items-center gap-3 text-xs text-faint">
            {hints < intro.bottleneck_hints.length && <Button variant="ghost" className="text-xs" onClick={() => setHints(hints + 1)}>Give me a hint</Button>}
            <button onClick={() => setRevealed(true)} className="underline-offset-2 hover:text-muted hover:underline">Show me the answer</button>
          </div>
        </div>
      )}
      {open && (
        <div className="mt-4 grid gap-3">
          {guided && solved && <p className="flex items-center gap-1.5 text-[13.5px] font-medium text-ok"><Check className="size-4" strokeWidth={2.5} />{wrong.length ? 'Found it.' : 'Found it on the first try.'}</p>}
          <Prose>{intro.bottleneck}</Prose>
          {brute && run ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-sunken px-3.5 py-2.5">
              <span className="text-[12.5px] text-muted">
                The shading shows how many times each line actually ran on a {state.lineCounts?.used_worst_case ? 'worst-case' : 'random'} input of size n. Switch sizes and watch the hot line grow.
              </span>
              <SizePicker runs={brute} n={run.n} setN={setN} />
            </div>
          ) : state.status === 'running' && <p className="text-xs text-faint">Counting how often each line runs…</p>}
        </div>
      )}
      <ContinueBar id="bottleneck" enabled={open} />
    </div>
  )
}
