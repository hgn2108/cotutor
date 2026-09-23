import clsx from 'clsx'
import { useState } from 'react'
import { Badge, Card } from '../../../components/ui'
import type { LineCountRun } from '../../../lib/types'
import { CodeView } from '../../viz/CodeView'
import { Verdict } from '../../viz/Player'
import { bigOOptions, normalizeBigO } from '../answers'
import { useLesson } from '../context'
import { SizePicker, useLineHeat } from '../lineHeat'
import { Callout, ContinueBar, Prose } from '../parts'

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
