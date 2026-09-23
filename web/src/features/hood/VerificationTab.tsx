import clsx from 'clsx'
import { ShieldCheck, ShieldQuestion } from 'lucide-react'
import { useState } from 'react'
import type { CaseDef, CaseResult } from '../../lib/types'
import type { RunState } from '../../lib/useRun'
import { Badge, Card, formatJson, Mono, SectionTitle, Waiting } from '../../components/ui'

const statusTone = { pass: 'ok', ran: 'neutral', fail: 'bad', error: 'bad', timeout: 'warn', skipped: 'neutral' } as const
const sourceLabel: Record<CaseDef['source'], [string, 'accent' | 'neutral' | 'warn']> = {
  example: ['example', 'accent'],
  reference: ['oracle', 'neutral'],
  stress: ['found by stress test', 'warn'],
}

export function VerificationTab({ state }: { state: RunState }) {
  const [attemptIdx, setAttemptIdx] = useState<number | null>(null)
  const { verifications, oracle, testPlan } = state
  if (!verifications.length) return <Waiting label="Waiting for the first verification run…" />
  const v = verifications[attemptIdx ?? verifications.length - 1]
  const byId = new Map(v.cases.map((c) => [c.id, c]))

  return (
    <div className="grid gap-4">
      <Card className="p-5">
        <div className="flex flex-wrap items-start gap-4">
          <div className="flex flex-1 gap-3">
            {oracle?.trusted ? <ShieldCheck className="mt-0.5 size-5 shrink-0 text-ok" /> : <ShieldQuestion className="mt-0.5 size-5 shrink-0 text-warn" />}
            <p className="text-[13.5px] leading-relaxed text-muted">
              {oracle?.trusted
                ? <>Expected outputs for generated cases come from a <span className="font-medium text-ink">brute-force oracle</span> that was first checked against the problem's own examples{oracle.has_checker && <>, and a <span className="font-medium text-ink">custom checker</span> accepts any valid answer</>}. After the tests pass, {v.stress_trials || 'hundreds of'} random inputs are compared against the oracle.</>
                : <>The oracle disagreed with the problem's examples, so it was not trusted. Only the examples are checked for exact answers; other cases just have to run without crashing.</>}
            </p>
          </div>
          {verifications.length > 1 && (
            <div className="flex rounded-lg bg-sunken p-0.5 text-xs">
              {verifications.map((x, i) => (
                <button key={i} onClick={() => setAttemptIdx(i)} className={clsx('rounded-md px-2.5 py-1', (attemptIdx ?? verifications.length - 1) === i ? 'bg-panel shadow-sm' : 'text-muted')}>
                  {i === 0 ? 'First run' : `After fix #${i}`} {x.verified ? '✓' : '✗'}
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      {v.load_error && (
        <Card className="border-bad/40 p-4 text-sm text-bad">
          {v.load_error.type}: {v.load_error.message} {v.load_error.where.join(' · ')}
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[13px]">
            <thead className="border-b border-line bg-sunken/60 text-[11px] uppercase tracking-wide text-muted">
              <tr><th className="px-4 py-2 font-semibold">Case</th><th className="px-3 py-2 font-semibold">Input</th><th className="px-3 py-2 font-semibold">Expected</th><th className="px-3 py-2 font-semibold">Got</th><th className="px-4 py-2 text-right font-semibold">Result</th></tr>
            </thead>
            <tbody>
              {v.results.map((r) => <Row key={r.id} r={r} c={byId.get(r.id)} />)}
            </tbody>
          </table>
        </div>
      </Card>

      {v.counterexample && (
        <Card className="border-warn/40 p-5">
          <SectionTitle>Counterexample from random stress testing</SectionTitle>
          <div className="grid gap-1.5 text-[13px]">
            <div><span className="text-muted">input </span><Mono>{formatJson(v.counterexample.args, 400)}</Mono></div>
            <div><span className="text-muted">oracle </span><Mono>{formatJson(v.counterexample.expected)}</Mono></div>
            {'got' in v.counterexample && <div><span className="text-muted">solution </span><Mono className="text-bad">{formatJson(v.counterexample.got)}</Mono></div>}
            {v.counterexample.error && <div className="text-bad">{v.counterexample.error.type}: {v.counterexample.error.message}</div>}
          </div>
        </Card>
      )}

      {testPlan && (
        <details className="group rounded-xl border border-line bg-panel">
          <summary className="cursor-pointer select-none px-5 py-3 text-sm font-medium text-muted hover:text-ink">Oracle, input generator{testPlan.checker_code ? ' and checker' : ''} written by the Test Designer</summary>
          <div className="grid gap-3 border-t border-line p-5">
            {[['Brute-force oracle', testPlan.reference_solution], ['Random input generator', testPlan.generator_code], ['Answer checker', testPlan.checker_code]]
              .filter(([, code]) => code.trim())
              .map(([title, code]) => (
                <div key={title}>
                  <div className="mb-1.5 text-xs font-medium text-muted">{title}</div>
                  <pre className="overflow-x-auto rounded-lg bg-sunken p-3 font-mono text-[12px] leading-relaxed">{code}</pre>
                </div>
              ))}
          </div>
        </details>
      )}
    </div>
  )
}

function Row({ r, c }: { r: CaseResult; c?: CaseDef }) {
  const [label, tone] = c ? sourceLabel[c.source] : ['', 'neutral' as const]
  return (
    <tr className="border-b border-line align-top last:border-0">
      <td className="px-4 py-2.5">
        <div className="font-medium">{c?.label ?? r.id}</div>
        <div className="mt-1 flex flex-wrap gap-1">{label && <Badge tone={tone}>{label}</Badge>}{c?.category && <Badge>{c.category}</Badge>}</div>
        {c?.rationale && <div className="mt-1 max-w-[220px] text-[11.5px] leading-4 text-faint">{c.rationale}</div>}
      </td>
      <td className="max-w-[260px] break-all px-3 py-2.5"><Mono>{formatJson(c?.args)}</Mono></td>
      <td className="max-w-[160px] break-all px-3 py-2.5"><Mono className="text-muted">{r.expected_source === 'none' ? '—' : formatJson(r.expected)}</Mono></td>
      <td className="max-w-[180px] break-all px-3 py-2.5">
        {r.error
          ? <span className="text-[12px] text-bad">{r.error.type}: {r.error.message}{r.error.where.length > 0 && <span className="text-faint"> ({r.error.where.at(-1)})</span>}</span>
          : <Mono className={r.status === 'fail' ? 'text-bad' : ''}>{formatJson(r.got)}</Mono>}
      </td>
      <td className="px-4 py-2.5 text-right">
        <Badge tone={statusTone[r.status]}>{r.status}</Badge>
        {r.ms !== undefined && <div className="mt-1 font-mono text-[10.5px] text-faint">{r.ms.toFixed(2)}ms</div>}
      </td>
    </tr>
  )
}
