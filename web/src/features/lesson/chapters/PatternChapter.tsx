import clsx from 'clsx'
import { Check, Lightbulb, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { seededShuffle } from '../answers'
import { useLesson } from '../context'
import { Callout, ContinueBar, Prose } from '../parts'

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
