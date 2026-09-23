import type { ReactNode } from 'react'
import type { Complexity } from '../../lib/types'
import type { RunState } from '../../lib/useRun'
import { Badge, Card, SectionTitle, Waiting } from '../../components/ui'

const W = 640, H = 320, PAD = { l: 56, r: 20, t: 16, b: 40 }

const REFS = [
  { name: 'O(n)', slope: 1, cls: 'stroke-viz-2' },
  { name: 'O(n²)', slope: 2, cls: 'stroke-viz-4' },
]

function niceTicks(lo: number, hi: number) {
  const ticks: number[] = []
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) ticks.push(10 ** e)
  return ticks.filter((t) => t >= lo / 1.01 && t <= hi * 1.01)
}

function fmtMs(v: number) {
  if (v >= 1000) return `${v / 1000}s`
  if (v >= 1) return `${v}ms`
  return `${+(v * 1000).toPrecision(2)}µs`
}

function Chart({ c }: { c: Complexity }) {
  const pts = c.points.filter(([, ms]) => ms > 0)
  if (pts.length < 2) return <p className="text-sm text-muted">Not enough timing points to plot.</p>
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1])
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)]
  const [y0, y1] = [Math.min(...ys) / 1.6, Math.max(...ys) * 1.6]
  const sx = (n: number) => PAD.l + ((Math.log(n) - Math.log(x0)) / (Math.log(x1) - Math.log(x0) || 1)) * (W - PAD.l - PAD.r)
  const sy = (ms: number) => H - PAD.b - ((Math.log(ms) - Math.log(y0)) / (Math.log(y1) - Math.log(y0))) * (H - PAD.t - PAD.b)
  // Anchor reference curves and the fitted line at the last (most reliable) measurement.
  const [ax, ay] = pts[pts.length - 1]
  const line = (slope: number) => {
    const at = (n: number) => ay * (n / ax) ** slope
    const segs: string[] = []
    for (let i = 0; i <= 24; i++) {
      const n = x0 * (x1 / x0) ** (i / 24)
      const v = at(n)
      if (v >= y0 && v <= y1) segs.push(`${segs.length ? 'L' : 'M'}${sx(n).toFixed(1)},${sy(v).toFixed(1)}`)
    }
    return segs.join('')
  }
  const measured = pts.map(([n, ms], i) => `${i ? 'L' : 'M'}${sx(n)},${sy(ms)}`).join('')
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[480px]" role="img" aria-label="Runtime versus input size, log-log">
        {niceTicks(y0, y1).map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={W - PAD.r} y1={sy(t)} y2={sy(t)} className="stroke-line" strokeDasharray="2 4" />
            <text x={PAD.l - 8} y={sy(t) + 4} textAnchor="end" className="fill-faint font-mono text-[10.5px]">{fmtMs(t)}</text>
          </g>
        ))}
        {xs.map((n) => (
          <text key={n} x={sx(n)} y={H - PAD.b + 18} textAnchor="middle" className="fill-faint font-mono text-[10.5px]">
            {n >= 1024 ? `${Math.round(n / 1024)}k` : n}
          </text>
        ))}
        <text x={(W + PAD.l) / 2} y={H - 4} textAnchor="middle" className="fill-muted text-[11px]">input size n (log scale)</text>
        {REFS.map((r) => <path key={r.name} d={line(r.slope)} fill="none" className={r.cls} strokeWidth={1.2} strokeDasharray="5 5" opacity={0.7} />)}
        <path d={measured} fill="none" className="stroke-viz-1" strokeWidth={2.4} strokeLinejoin="round" />
        {pts.map(([n, ms]) => (
          <circle key={n} cx={sx(n)} cy={sy(ms)} r={3.5} className="fill-panel stroke-viz-1" strokeWidth={2}>
            <title>n = {n.toLocaleString()}: {fmtMs(+ms.toPrecision(3))}</title>
          </circle>
        ))}
      </svg>
      <div className="mt-2 flex flex-wrap justify-center gap-4 text-[12px] text-muted">
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 rounded bg-viz-1" />measured</span>
        {REFS.map((r) => <span key={r.name} className="flex items-center gap-1.5"><span className={`h-0 w-5 border-t border-dashed ${r.cls.replace('stroke', 'border')}`} />{r.name} reference</span>)}
      </div>
    </div>
  )
}

export function TimingTab({ state }: { state: RunState }) {
  const c = state.complexity
  if (!c) {
    if (state.status === 'running') return <Waiting label="Timing the verified solution on growing inputs…" />
    return <Card className="p-5 text-sm text-muted">No timing data for this run (the test designer did not provide an input generator).</Card>
  }
  const tone = c.verdict === 'consistent' ? 'ok' : c.verdict === 'inconclusive' ? 'neutral' : 'warn'
  return (
    <div className="grid gap-4">
      <Card className="p-5">
        <SectionTitle aside={<Badge tone={tone}>{c.verdict.replaceAll('_', ' ')}</Badge>}>Empirical complexity</SectionTitle>
        <div className="mb-4 grid grid-cols-3 gap-3">
          <Stat label="Claimed" value={c.claimed} />
          <Stat label="Measured growth" value={c.slope !== null ? <>n<sup>{c.slope.toFixed(2)}</sup></> : '—'} />
          <Stat label="Largest input timed" value={c.points.length ? `n = ${c.points.at(-1)![0].toLocaleString()}` : '—'} />
        </div>
        <Chart c={c} />
        <p className="mt-4 text-[13px] leading-relaxed text-muted">
          {c.note} The solution is run on {c.used_worst_case ? 'worst-case' : 'random'} inputs from the Test Designer's generator, doubling n until one run takes long enough to measure. The slope of log(time) against log(n) estimates the exponent: about 1 for linear, a bit above 1 for n log n, about 2 for quadratic.
          {state.execLog.some((e) => e.kind === 'complexity') && ' These timings come from Python running as WebAssembly in your browser, so absolute times are slower than native Python. The growth rate is what matters.'}
        </p>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg bg-sunken px-3 py-2.5">
      <div className="text-[11px] text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-[15px] font-semibold">{value}</div>
    </div>
  )
}
