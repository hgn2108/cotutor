import { ExternalLink, Search } from 'lucide-react'
import { Badge } from '../../../components/ui'
import { useLesson } from '../context'
import { ArgsInline, Callout, ContinueBar, HighlightedText, Prose } from '../parts'

export function ProblemChapter() {
  const { state, guided, isDone, roadmap } = useLesson()
  const { spec, lessonIntro } = state
  const showSignals = !!lessonIntro && (!guided || isDone('pattern'))
  return (
    <div>
      {state.byName ? (
        <div className="rounded-xl border border-line bg-sunken/60 px-4 py-3.5">
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">The problem, in our own words</span>
            {roadmap && (
              <a href={roadmap.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs font-medium text-accent hover:underline">
                Read the original on LeetCode<ExternalLink className="size-3" />
              </a>
            )}
          </div>
          {spec ? (
            <p className="whitespace-pre-line text-[14px] leading-relaxed">
              <HighlightedText text={spec.summary} phrases={showSignals ? lessonIntro.signals.map((s) => s.phrase) : []} />
            </p>
          ) : <p className="text-sm text-faint">Reconstructing the problem from its name…</p>}
        </div>
      ) : (
        <div className="whitespace-pre-wrap rounded-xl border border-line bg-sunken/60 px-4 py-3.5 text-[14px] leading-relaxed">
          <HighlightedText text={state.problem} phrases={showSignals ? lessonIntro.signals.map((s) => s.phrase) : []} />
        </div>
      )}
      {spec && (
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            {!state.byName && <><div className="mb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">In other words</div>
            <Prose className="whitespace-pre-line">{spec.summary}</Prose></>}
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
