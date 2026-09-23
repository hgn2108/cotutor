import { Editor } from '@monaco-editor/react'
import clsx from 'clsx'
import { BookOpen, Check, ChevronRight, Copy, Lightbulb, Repeat, TriangleAlert, X } from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import type { CaseDef, CaseResult, Json, LineCountRun } from '../../lib/types'
import { Flowchart } from '../Flowchart'
import { Badge, Button, Card, formatJson } from '../ui'
import { CodeView } from '../viz/CodeView'
import { Player, Verdict } from '../viz/Player'
import { answersMatch, bigOOptions, normalizeBigO, parseAnswer } from './answers'
import { SizePicker, useLineHeat } from './ChaptersStart'
import { useLesson } from './context'
import { ArgsInline, Callout, ContinueBar, Prose, ThinkFirst } from './parts'

export function InsightChapter() {
  const { state, dark } = useLesson()
  const solution = state.solutions.at(-1)!
  const ex = state.explanation
  const [revealed, setRevealed] = useState(false)
  const [copied, setCopied] = useState(false)
  return (
    <div>
      <ThinkFirst
        prompt="You know where the wasted work is. How could you avoid repeating it?"
        placeholder="e.g. remember something so you don't have to search again…" revealLabel="Show the key insight"
        revealed={revealed} onReveal={() => setRevealed(true)}
      >
        <Callout icon={<Lightbulb className="size-4" />} title={solution.approach}>
          {state.lessonDeep?.insight ?? solution.key_insight}
          {ex?.intuition && <p className="mt-1.5 text-muted">{ex.intuition}</p>}
        </Callout>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-line px-4 py-2">
              <span className="font-mono text-xs text-muted">solution.py</span>
              {state.summary?.verified && <Badge tone="ok">verified</Badge>}
              <Button variant="ghost" className="ml-auto text-xs" onClick={async () => { await navigator.clipboard.writeText(solution.code); setCopied(true); setTimeout(() => setCopied(false), 1500) }}>
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}{copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <Editor
              height={Math.min(460, solution.code.split('\n').length * 19 + 28)} language="python" value={solution.code} theme={dark ? 'vs-dark' : 'light'}
              options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, fontFamily: 'JetBrains Mono, monospace', lineNumbersMinChars: 3, scrollBeyondLastLine: false, renderLineHighlight: 'none', padding: { top: 10, bottom: 10 }, scrollbar: { alwaysConsumeMouseWheel: false } }}
            />
          </Card>
          {ex && (
            <Card className="p-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Control flow</div>
              <Flowchart nodes={ex.flow_nodes} edges={ex.flow_edges} />
            </Card>
          )}
        </div>
        <details className="mt-3 rounded-xl border border-line bg-panel">
          <summary className="cursor-pointer select-none px-4 py-2.5 text-[13px] font-medium text-muted hover:text-ink">The reasoning, step by step</summary>
          <ol className="grid gap-3 border-t border-line p-4">
            {solution.steps.map((s, k) => (
              <li key={k} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-sunken font-mono text-[11px] font-semibold text-muted">{k + 1}</span>
                <div><div className="text-[13.5px] font-medium">{s.title}</div><p className="mt-0.5 text-[13px] leading-relaxed text-muted">{s.detail}</p></div>
              </li>
            ))}
          </ol>
        </details>
      </ThinkFirst>
      <ContinueBar id="insight" enabled={revealed} />
    </div>
  )
}

export function WatchChapter() {
  const { state, guided, record } = useLesson()
  const [progress, setProgress] = useState({ reachedEnd: false, answered: 0, total: 0 })
  const onProgress = useCallback((p: { reachedEnd: boolean; answered: number; correct: number; total: number }) => {
    setProgress(p)
    if (p.total) record('watch', { correct: p.correct, total: p.total })
  }, [record])
  return (
    <div>
      {guided && (
        <Prose className="mb-3 text-muted">
          Step through the solution on a small input. At the <span className="font-medium text-viz-3">●</span> checkpoints, predict what happens before you see it.
        </Prose>
      )}
      <Player trace={state.trace!} explanation={state.explanation} guided={guided} onProgress={onProgress} />
      <ContinueBar id="watch" enabled={progress.reachedEnd || (progress.total > 0 && progress.answered >= progress.total)} hint={guided && !progress.reachedEnd ? 'Step through to the end to continue.' : undefined} />
    </div>
  )
}

function StepGrowth({ solution, brute }: { solution: LineCountRun[]; brute?: LineCountRun[] }) {
  const W = 520, H = 220, P = { l: 48, r: 64, t: 14, b: 30 }
  const ns = solution.map((r) => r.n)
  const series = [
    { name: 'brute force', runs: brute ?? [], cls: 'stroke-viz-4', fill: 'fill-viz-4' },
    { name: 'optimized', runs: solution, cls: 'stroke-viz-1', fill: 'fill-viz-1' },
  ].filter((s) => s.runs.length)
  const maxY = Math.max(1, ...series.flatMap((s) => s.runs.map((r) => r.total)))
  const sx = (n: number) => P.l + (ns.indexOf(n) / Math.max(1, ns.length - 1)) * (W - P.l - P.r)
  const sy = (v: number) => H - P.b - (v / maxY) * (H - P.t - P.b)
  const ratio = (runs: LineCountRun[]) => (runs.length >= 2 ? runs.at(-1)!.total / Math.max(1, runs.at(-2)!.total) : null)
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[560px]" role="img" aria-label="Steps executed versus input size">
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={P.l} x2={W - P.r} y1={sy(maxY * f)} y2={sy(maxY * f)} className="stroke-line" strokeDasharray="2 4" />
            <text x={P.l - 8} y={sy(maxY * f) + 4} textAnchor="end" className="fill-faint font-mono text-[10.5px]">{Math.round(maxY * f).toLocaleString()}</text>
          </g>
        ))}
        {ns.map((n) => <text key={n} x={sx(n)} y={H - 8} textAnchor="middle" className="fill-faint font-mono text-[10.5px]">n={n}</text>)}
        {series.map((s) => (
          <g key={s.name}>
            <path d={s.runs.map((r, k) => `${k ? 'L' : 'M'}${sx(r.n)},${sy(r.total)}`).join('')} fill="none" className={s.cls} strokeWidth={2.4} strokeLinejoin="round" />
            {s.runs.map((r) => <circle key={r.n} cx={sx(r.n)} cy={sy(r.total)} r={3.5} className={clsx('stroke-panel', s.fill)} strokeWidth={1.5} />)}
            {s.runs.length > 0 && (
              <text x={sx(s.runs.at(-1)!.n) + 8} y={sy(s.runs.at(-1)!.total) + 4} className={clsx('font-mono text-[11px] font-semibold', s.fill)}>{s.runs.at(-1)!.total.toLocaleString()}</text>
            )}
          </g>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-[12.5px]">
        {series.map((s) => {
          const r = ratio(s.runs)
          return (
            <span key={s.name} className="flex items-center gap-1.5">
              <span className={clsx('h-0.5 w-4 rounded', s.cls.replace('stroke', 'bg'))} />
              <span className="text-muted">{s.name}:</span>
              <span className="font-mono">{s.runs.map((x) => x.total.toLocaleString()).join(' → ')} steps</span>
              {r && <Badge tone={r > 3 ? 'warn' : 'ok'} className="font-mono">×{r.toFixed(1)} per doubling</Badge>}
            </span>
          )
        })}
      </div>
    </div>
  )
}

export function ComplexityChapter() {
  const { state, guided, isDone, record } = useLesson()
  const solution = state.solutions.at(-1)!
  const deep = state.lessonDeep!
  const correct = normalizeBigO(solution.time_complexity)
  const [pick, setPick] = useState<string | null>(null)
  const [n, setN] = useState<number | null>(null)
  const open = !guided || !correct || pick !== null || isDone('complexity')
  const counts = state.lineCounts
  const { run, heat } = useLineHeat(counts?.solution, n)
  const derivationGutter = Object.fromEntries(deep.derivation.map((d) => [d.line, (
    <span key={d.line} title={d.note} className="rounded bg-accent-soft px-1.5 py-px text-[11px] font-medium text-accent">{d.cost}</span>
  )]))

  const choose = (o: string) => {
    if (pick) return
    setPick(o)
    record('complexity', { correct: o === correct ? 1 : 0, total: 1 })
  }

  return (
    <div>
      {guided && correct && (
        <div className="mb-4">
          <Prose className="mb-2.5 font-medium">Before the explanation: what's the time complexity of the optimized solution?</Prose>
          <div className="flex flex-wrap gap-2">
            {bigOOptions.map((o) => (
              <button key={o} onClick={() => choose(o)} disabled={!!pick}
                className={clsx('rounded-lg border px-3 py-1.5 font-mono text-[13px] transition',
                  !pick && 'border-line bg-panel hover:border-accent/60',
                  pick && o === correct && 'border-ok/60 bg-ok-soft text-ok',
                  pick === o && o !== correct && 'border-bad/50 bg-bad-soft text-bad',
                  pick && o !== correct && pick !== o && 'border-line opacity-50')}>{o}</button>
            ))}
          </div>
          {pick && <div className="mt-2"><Verdict correct={pick === correct}>It's <b>{solution.time_complexity}</b>. Here's why.</Verdict></div>}
        </div>
      )}
      {open && (
        <div className="grid gap-4">
          {counts && (
            <Card className="p-4">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Count the steps, don't just trust the label</div>
              <p className="mb-3 text-[13px] text-muted">Total lines executed on {counts.used_worst_case ? 'worst-case' : 'random'} inputs as n doubles. Doubling n and seeing about ×2 steps means linear growth; about ×4 means quadratic.</p>
              <StepGrowth solution={counts.solution} brute={counts.brute_force} />
            </Card>
          )}
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
            <div>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Where the cost comes from</span>
                {counts && <SizePicker runs={counts.solution} n={run?.n ?? null} setN={setN} />}
              </div>
              <CodeView code={deep.code} heat={heat} gutter={derivationGutter} maxHeight={420} />
              {run && <p className="mt-1.5 text-[11.5px] text-faint">Shading: how often each line ran when n = {run.n}. Badges: the cost of each important line.</p>}
            </div>
            <div className="grid content-start gap-3">
              {deep.derivation.map((d) => (
                <div key={d.line} className="flex gap-3 text-[13px]">
                  <span className="w-12 shrink-0 font-mono text-[11.5px] text-faint">line {d.line}</span>
                  <div><span className="font-medium">{d.cost}</span><span className="text-muted">: {d.note}</span></div>
                </div>
              ))}
              <Callout tone="ok" title={`Time: ${solution.time_complexity}`}>{deep.time_summary}</Callout>
              <Callout tone="accent" title={`Space: ${solution.space_complexity}`}>{deep.space_summary}</Callout>
              {state.complexity?.slope != null && (
                <p className="text-[11.5px] text-faint">Also checked at scale: timing up to n = {state.complexity.points.at(-1)?.[0].toLocaleString()} grew about n^{state.complexity.slope.toFixed(2)} ({state.complexity.verdict.replaceAll('_', ' ')}). See Under the hood.</p>
              )}
            </div>
          </div>
        </div>
      )}
      <ContinueBar id="complexity" enabled={open} />
    </div>
  )
}

interface EdgeItem { def: CaseDef; result: CaseResult }

function pickEdgeCases(defs: CaseDef[], results: CaseResult[]): EdgeItem[] {
  const byId = new Map(results.map((r) => [r.id, r]))
  const usable = defs
    .map((def) => ({ def, result: byId.get(def.id)! }))
    .filter((x) => x.result && x.result.expected_source !== 'none' && x.def.source !== 'stress' && x.def.category !== 'large'
      && JSON.stringify(x.def.args).length < 90)
  const rank = (x: EdgeItem) => (x.def.category === 'tricky' ? 0 : x.def.category === 'edge' ? 1 : 2)
  return usable.sort((a, b) => rank(a) - rank(b)).slice(0, 4)
}

function EdgeCase({ item, index, onResult }: { item: EdgeItem; index: number; onResult: (correct: boolean | null) => void }) {
  const { state, guided } = useLesson()
  const spec = state.spec
  const [guess, setGuess] = useState('')
  const [outcome, setOutcome] = useState<boolean | null | undefined>(undefined)
  const expected = item.result.expected as Json
  const multi = spec?.multiple_valid_answers
  const done = !guided || outcome !== undefined
  const check = () => {
    const g = parseAnswer(guess)
    const ok = g.ok && answersMatch(g.value, expected, spec?.comparison ?? 'exact')
    setOutcome(ok)
    onResult(ok)
  }
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12px] font-semibold text-faint">#{index + 1}</span>
        <span className="text-[13.5px] font-medium">{item.def.label}</span>
        {item.def.category && <Badge>{item.def.category}</Badge>}
      </div>
      <div className="mt-2"><ArgsInline args={item.def.args} spec={spec} /></div>
      {!done ? (
        <form className="mt-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); check() }}>
          <input value={guess} onChange={(e) => setGuess(e.target.value)} placeholder="Your predicted output"
            className="w-56 rounded-lg border border-line bg-sunken px-3 py-1.5 font-mono text-[13px] outline-none focus:border-accent" />
          <Button variant="outline" type="submit" disabled={!guess.trim()}>Check</Button>
          <Button variant="ghost" type="button" className="text-xs" onClick={() => { setOutcome(null); onResult(null) }}>Reveal</Button>
        </form>
      ) : (
        <div className="mt-3 grid gap-1.5">
          {guided
            ? <Verdict correct={outcome ?? null}>Expected <code className="font-mono">{formatJson(expected)}</code>{multi && outcome === false ? ' (other answers can also be valid here)' : ''}</Verdict>
            : <div className="text-[13px]"><span className="text-muted">Output: </span><code className="font-mono font-semibold">{formatJson(expected)}</code></div>}
          {item.def.rationale && <p className="text-[12.5px] leading-relaxed text-muted">Why it matters: {item.def.rationale}</p>}
        </div>
      )}
    </div>
  )
}

export function EdgesChapter() {
  const { state, guided, record } = useLesson()
  const last = state.verifications.at(-1)!
  const items = useMemo(() => pickEdgeCases(last.cases, last.results), [last])
  const [results, setResults] = useState<Record<number, boolean | null>>({})
  const answered = Object.keys(results).length
  const set = (k: number, v: boolean | null) => {
    const next = { ...results, [k]: v }
    setResults(next)
    record('edges', { correct: Object.values(next).filter(Boolean).length, total: items.length })
  }
  if (!items.length) return <div><Prose className="text-muted">No small edge cases to practice on for this problem.</Prose><ContinueBar id="edges" enabled /></div>
  return (
    <div>
      <Prose className="mb-3 text-muted">
        {guided ? 'Predict what the solution returns for each tricky input. These are the cases that break sloppy solutions.' : 'Tricky inputs that break sloppy solutions, with their correct outputs.'}
      </Prose>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((it, k) => <EdgeCase key={it.def.id} item={it} index={k} onResult={(v) => set(k, v)} />)}
      </div>
      <ContinueBar id="edges" enabled={answered >= items.length} hint={guided && answered < items.length ? `${answered}/${items.length} answered` : undefined} />
    </div>
  )
}

export function RecapChapter() {
  const { state, guided, scores, onSolve } = useLesson()
  const deep = state.lessonDeep
  const intro = state.lessonIntro
  const ex = state.explanation
  const mistakes = deep?.mistakes?.length ? deep.mistakes : ex?.pitfalls ?? []
  const scoreItems = ([['pattern', 'Pattern'], ['bottleneck', 'Bottleneck'], ['watch', 'Predictions'], ['complexity', 'Complexity'], ['edges', 'Edge cases']] as const)
    .filter(([id]) => scores[id]).map(([id, label]) => ({ label, ...scores[id]! }))
  return (
    <div className="grid gap-4">
      {deep && (
        <div className="rounded-2xl border border-accent/30 bg-accent-soft/60 p-5">
          <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-accent"><BookOpen className="size-3.5" />Remember this</div>
          <p className="text-[16px] font-medium leading-relaxed">{deep.takeaway}</p>
          {intro && <p className="mt-2 text-[13px] text-muted">Pattern: <span className="font-medium text-ink">{intro.pattern}</span> · brute force {intro.brute_force_time} → optimized {state.solutions.at(-1)?.time_complexity}</p>}
        </div>
      )}
      {guided && scoreItems.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {scoreItems.map((s) => (
            <Badge key={s.label} tone={s.correct === s.total ? 'ok' : s.correct ? 'warn' : 'neutral'} className="px-2 py-1 text-[12px]">
              {s.correct === s.total ? <Check className="size-3.5" /> : s.correct ? null : <X className="size-3.5" />}{s.label} {s.correct}/{s.total}
            </Badge>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {mistakes.length > 0 && (
          <Card className="p-4">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Mistakes to avoid</div>
            <ul className="grid gap-2">
              {mistakes.map((m, k) => <li key={k} className="flex gap-2 text-[13px] leading-relaxed"><TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-warn" />{m}</li>)}
            </ul>
            {state.debugAttempts.length > 0 && (
              <p className="mt-3 text-[12px] text-faint">The first AI-written draft of this solution had a bug too. It was caught by random testing and fixed ({state.debugAttempts.length} round{state.debugAttempts.length > 1 ? 's' : ''}).</p>
            )}
          </Card>
        )}
        {ex && ex.similar_problems.length > 0 && (
          <Card className="p-4">
            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted"><Repeat className="size-3.5" />Practice the same pattern</div>
            <div className="grid gap-1.5">
              {ex.similar_problems.map((p) => (
                <button key={p} onClick={() => onSolve(`LeetCode problem: ${p}. Solve and explain it.`)}
                  className="group flex items-center justify-between rounded-lg border border-line px-3 py-2 text-left text-[13px] hover:border-accent/50">
                  {p}<ChevronRight className="size-4 text-faint group-hover:text-accent" />
                </button>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
