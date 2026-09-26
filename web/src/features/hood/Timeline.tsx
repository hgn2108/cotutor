import clsx from 'clsx'
import { AlertTriangle, Check, Cpu, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { ExecLogEntry } from '../../lib/useRun'
import type { StageEvent } from '../../lib/types'
import { Spinner } from '../../components/ui'

const PARALLEL = new Set(['design_tests', 'solve', 'complexity', 'explain'])

// Plain-language labels (older recordings still carry the original wording).
const LABELS: Record<string, string> = {
  design_tests: 'Test Designer: edge cases + a slow reference solution',
  oracle: 'Check the answer key: reference solution vs. examples',
  naive_check: 'Confirm the slow version is really slow',
}

function plain(detail: string): string {
  return detail
    .replace(/brute-force oracle/gi, 'reference solution')
    .replace(/\boracle-generated\b/gi, 'generated')
    .replace(/\boracle\b/gi, 'reference solution')
    .replace(/random stress trials/gi, 'random inputs')
    .replace(/random stress test(ing)?/gi, 'random testing')
    .replace(/Stopped because another step failed\./, 'Stopped before it finished.')
    .replace(/Sweep generator stopped growing at n=(\d+) \(input size \d+\)\./, 'Inputs couldn’t be made larger than n = $1, so timing is too small to measure.')
}

function StatusIcon({ status }: { status: StageEvent['status'] }) {
  const base = 'flex size-6 shrink-0 items-center justify-center rounded-full'
  if (status === 'running') return <span className={clsx(base, 'bg-accent-soft text-accent')}><Spinner className="size-3" /></span>
  if (status === 'done') return <span className={clsx(base, 'bg-ok-soft text-ok')}><Check className="size-3.5" strokeWidth={3} /></span>
  if (status === 'failed') return <span className={clsx(base, 'bg-bad-soft text-bad')}><X className="size-3.5" strokeWidth={3} /></span>
  return <span className={clsx(base, 'bg-warn-soft text-warn')}><AlertTriangle className="size-3.5" /></span>
}

export function Timeline({ stages, execLog, running }: { stages: StageEvent[]; execLog: ExecLogEntry[]; running: boolean }) {
  const execMs = execLog.reduce((a, e) => a + e.ms, 0)
  return (
    <div>
      <ol className="relative">
        <AnimatePresence initial={false}>
          {stages.map((s, i) => {
            const label = LABELS[s.id] ?? s.label
            const [agent, task] = label.includes(':') ? label.split(/:(.*)/s, 2) : ['', label]
            return (
              <motion.li
                key={s.id} layout
                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
                className="relative flex gap-3 pb-4"
              >
                {i < stages.length - 1 && <span className="absolute left-3 top-7 h-[calc(100%-1.5rem)] w-px bg-line" />}
                <StatusIcon status={s.status} />
                <div className="min-w-0 flex-1 pt-0.5">
                  <div className="flex flex-wrap items-baseline gap-x-1.5 text-[13px] leading-5">
                    {agent && <span className="font-semibold">{agent}</span>}
                    <span className="text-muted">{task.trim()}</span>
                    {PARALLEL.has(s.id) && <span className="rounded bg-sunken px-1 text-[10px] font-medium uppercase tracking-wide text-faint">parallel</span>}
                  </div>
                  {s.detail && <p className={clsx('mt-0.5 text-[12px] leading-[1.45]', s.status === 'failed' ? 'text-bad' : s.status === 'warning' ? 'text-warn' : 'text-muted')}>{plain(s.detail)}</p>}
                  {s.status !== 'running' && (s.ms !== undefined) && (
                    <div className="mt-1 flex gap-2 font-mono text-[10.5px] text-faint">
                      <span>{s.ms < 1000 ? `${s.ms}ms` : `${(s.ms / 1000).toFixed(1)}s`}</span>
                      {!!s.tokens && <span>{s.tokens.toLocaleString()} tok</span>}
                      {s.models?.map((m) => <span key={m}>{m}</span>)}
                    </div>
                  )}
                </div>
              </motion.li>
            )
          })}
        </AnimatePresence>
        {running && stages.length === 0 && (
          <li className="flex items-center gap-3 text-sm text-muted"><Spinner />Connecting to agents…</li>
        )}
      </ol>
      {execLog.length > 0 && (
        <div className="mt-2 flex items-center gap-2 rounded-lg bg-sunken px-3 py-2 text-[11.5px] text-muted">
          <Cpu className="size-3.5 shrink-0" />
          <span>{execLog.length} sandboxed executions in your browser · {(execMs / 1000).toFixed(1)}s total
            {execLog.some((e) => e.outcome === 'timeout') && <span className="text-warn"> · {execLog.filter((e) => e.outcome === 'timeout').length} killed on timeout</span>}
          </span>
        </div>
      )}
    </div>
  )
}
