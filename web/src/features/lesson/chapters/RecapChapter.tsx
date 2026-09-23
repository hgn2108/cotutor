import { BookOpen, Check, ChevronRight, Repeat, TriangleAlert, X } from 'lucide-react'
import { Badge, Card } from '../../../components/ui'
import { useLesson } from '../context'

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
