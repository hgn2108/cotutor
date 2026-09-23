import clsx from 'clsx'
import type { ReactNode } from 'react'
import type { LineCountRun } from '../../lib/types'

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
