import clsx from 'clsx'
import { ArrowDown, Eye } from 'lucide-react'
import { type ReactNode, useState } from 'react'
import type { Json, ProblemSpec } from '../../lib/types'
import { Button, formatJson } from '../../components/ui'
import { type ChapterId, useLesson } from './context'

/** Guided-mode footer: move on once the chapter's task is done (or skip it). */
export function ContinueBar({ id, enabled, label = 'Continue', hint }: { id: ChapterId; enabled: boolean; label?: string; hint?: string }) {
  const { guided, isDone, complete } = useLesson()
  if (!guided || isDone(id)) return null
  return (
    <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-line pt-4">
      <Button onClick={() => complete(id)} disabled={!enabled}>{label}<ArrowDown className="size-3.5" /></Button>
      {!enabled && (
        <button onClick={() => complete(id)} className="text-xs text-faint underline-offset-2 hover:text-muted hover:underline">Skip this step</button>
      )}
      {hint && <span className="text-xs text-faint">{hint}</span>}
    </div>
  )
}

/**
 * "Think first, then reveal": in guided mode the content stays hidden until the learner has
 * had a go (optionally writing their idea down). Walkthrough mode shows it immediately.
 */
export function ThinkFirst({ prompt, placeholder, revealLabel = 'Reveal', onReveal, revealed, children }: {
  prompt: ReactNode; placeholder: string; revealLabel?: string
  onReveal: () => void; revealed: boolean; children: ReactNode
}) {
  const { guided } = useLesson()
  const [text, setText] = useState('')
  if (!guided || revealed) {
    return (
      <>
        {guided && text.trim() && (
          <div className="mb-4 rounded-lg border border-dashed border-line px-3.5 py-2.5 text-[13px] text-muted">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-faint">Your idea</span>
            <p className="mt-0.5 whitespace-pre-wrap">{text}</p>
          </div>
        )}
        {children}
      </>
    )
  }
  return (
    <div className="rounded-xl border border-accent/30 bg-accent-soft/50 p-4">
      <div className="text-[14px] font-medium">{prompt}</div>
      <textarea
        value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder={placeholder}
        className="mt-3 w-full resize-y rounded-lg border border-line bg-panel px-3 py-2 text-[13.5px] outline-none placeholder:text-faint focus:border-accent"
      />
      <div className="mt-2.5 flex items-center gap-3">
        <Button onClick={onReveal}><Eye className="size-3.5" />{revealLabel}</Button>
        <span className="text-xs text-faint">Writing it down, even roughly, makes it stick.</span>
      </div>
    </div>
  )
}

export function Callout({ tone = 'accent', icon, title, children, className }: {
  tone?: 'accent' | 'ok' | 'warn'; icon?: ReactNode; title?: ReactNode; children: ReactNode; className?: string
}) {
  const bg = { accent: 'bg-accent-soft', ok: 'bg-ok-soft', warn: 'bg-warn-soft' }[tone]
  const fg = { accent: 'text-accent', ok: 'text-ok', warn: 'text-warn' }[tone]
  return (
    <div className={clsx('flex gap-3 rounded-lg p-3.5', bg, className)}>
      {icon && <span className={clsx('mt-0.5 shrink-0', fg)}>{icon}</span>}
      <div className="min-w-0 text-[13.5px] leading-relaxed">
        {title && <div className="font-semibold">{title}</div>}
        {children}
      </div>
    </div>
  )
}

export function Prose({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={clsx('text-[14px] leading-relaxed text-ink/90', className)}>{children}</p>
}

/** Render call arguments with their parameter names: `nums = [2, 7], target = 9`.
 *  Design problems read as a call sequence: `LRUCache(2) → put(1, 1) → get(1)`. */
export function ArgsInline({ args, spec }: { args: Json[]; spec?: ProblemSpec }) {
  if (spec?.kind === 'design' && Array.isArray(args[0]) && Array.isArray(args[1])) {
    const ops = args[0] as Json[], opArgs = args[1] as Json[]
    return (
      <span className="font-mono text-[12.5px]">
        {ops.map((op, k) => (
          <span key={k}>
            {k > 0 && <span className="text-faint"> → </span>}
            <span className={k === 0 ? 'font-semibold' : ''}>{String(op)}</span>
            <span className="text-muted">({Array.isArray(opArgs[k]) ? (opArgs[k] as Json[]).map((a) => formatJson(a, 30)).join(', ') : ''})</span>
          </span>
        ))}
      </span>
    )
  }
  return (
    <span className="font-mono text-[12.5px]">
      {args.map((a, k) => (
        <span key={k}>
          {k > 0 && <span className="text-faint">, </span>}
          {spec?.params[k] && <span className="text-muted">{spec.params[k].name} = </span>}
          {formatJson(a, 80)}
        </span>
      ))}
    </span>
  )
}

/** Highlight the Coach's signal phrases inside the original statement. */
export function HighlightedText({ text, phrases }: { text: string; phrases: string[] }) {
  const usable = phrases.filter((p) => p.trim().length > 2 && text.toLowerCase().includes(p.toLowerCase()))
  if (!usable.length) return <>{text}</>
  const escaped = usable.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).sort((a, b) => b.length - a.length)
  const parts = text.split(new RegExp(`(${escaped.join('|')})`, 'gi'))
  return (
    <>
      {parts.map((part, k) =>
        usable.some((p) => p.toLowerCase() === part.toLowerCase())
          ? <mark key={k} className="rounded bg-viz-3/25 px-0.5 text-ink">{part}</mark>
          : <span key={k}>{part}</span>)}
    </>
  )
}
