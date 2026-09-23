import { BadgeCheck, Bug, Dices, FlaskConical, Gauge, History, ShieldAlert } from 'lucide-react'
import type { RunState } from '../lib/useRun'
import { Badge, difficultyTone } from './ui'

const verdictText = {
  consistent: 'matches claim',
  slower_than_claimed: 'slower than claimed',
  faster_than_claimed: 'faster than claimed',
  inconclusive: 'inconclusive',
} as const

export function SummaryBar({ state }: { state: RunState }) {
  const { spec, summary, complexity, verifications, debugAttempts } = state
  const last = verifications.at(-1)
  const solution = state.solutions.at(-1)
  const passed = last?.results.filter((r) => r.status === 'pass' || r.status === 'ran').length ?? 0
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-xl font-semibold tracking-tight">{spec?.title ?? 'Analyzing problem…'}</h1>
        {spec && <Badge tone={difficultyTone[spec.difficulty]}>{spec.difficulty}</Badge>}
        {spec?.pattern_tags.map((t) => <Badge key={t}>{t}</Badge>)}
      </div>
      {spec && <p className="max-w-3xl text-[13.5px] leading-relaxed text-muted">{spec.summary}</p>}
      <div className="flex flex-wrap gap-1.5">
        {summary && (summary.verified
          ? <Badge tone="ok"><BadgeCheck className="size-3.5" />Verified</Badge>
          : <Badge tone="bad"><ShieldAlert className="size-3.5" />Not verified</Badge>)}
        {last && <Badge tone={last.verified ? 'ok' : 'neutral'}><FlaskConical className="size-3.5" />{passed}/{last.results.length} tests</Badge>}
        {!!last?.stress_trials && <Badge tone="ok"><Dices className="size-3.5" />{last.stress_trials} random trials</Badge>}
        {debugAttempts.length > 0 && <Badge tone="warn"><Bug className="size-3.5" />{debugAttempts.length} debug round{debugAttempts.length > 1 ? 's' : ''}</Badge>}
        {solution && <Badge><Gauge className="size-3.5" />{solution.time_complexity} time · {solution.space_complexity} space</Badge>}
        {complexity && complexity.slope !== null && (
          <Badge tone={complexity.verdict === 'consistent' ? 'ok' : complexity.verdict === 'inconclusive' ? 'neutral' : 'warn'}>
            measured ≈ n<sup>{complexity.slope.toFixed(2)}</sup> · {verdictText[complexity.verdict]}
          </Badge>
        )}
        {summary?.replayed && (
          <Badge tone="accent" title={summary.recording === 'scripted' ? 'Agent responses are scripted for this offline demo; test, stress and timing results come from real execution when it was recorded.' : 'Replayed from a previous verified run'}>
            <History className="size-3.5" />{summary.recording === 'scripted' ? 'Offline demo (scripted agents)' : 'Replayed run'}
          </Badge>
        )}
      </div>
    </div>
  )
}
