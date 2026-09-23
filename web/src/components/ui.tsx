import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx('rounded-xl border border-line bg-panel', className)}>{children}</div>
}

export function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-3">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">{children}</h3>
      {aside}
    </div>
  )
}

type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'bad'
const toneClass: Record<Tone, string> = {
  neutral: 'bg-sunken text-muted border-line',
  accent: 'bg-accent-soft text-accent border-transparent',
  ok: 'bg-ok-soft text-ok border-transparent',
  warn: 'bg-warn-soft text-warn border-transparent',
  bad: 'bg-bad-soft text-bad border-transparent',
}

export function Badge({ tone = 'neutral', children, className, title }: { tone?: Tone; children: ReactNode; className?: string; title?: string }) {
  return (
    <span title={title} className={clsx('inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium leading-4 whitespace-nowrap', toneClass[tone], className)}>
      {children}
    </span>
  )
}

export function Button({ variant = 'primary', className, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'outline' }) {
  return (
    <button
      {...props}
      className={clsx(
        'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50',
        variant === 'primary' && 'bg-accent px-4 py-2 text-white shadow-sm hover:brightness-110 dark:text-[#0e0e13]',
        variant === 'outline' && 'border border-line bg-panel px-3 py-1.5 text-ink hover:bg-sunken',
        variant === 'ghost' && 'px-2 py-1.5 text-muted hover:bg-sunken hover:text-ink',
        className,
      )}
    />
  )
}

export function Spinner({ className }: { className?: string }) {
  return <span className={clsx('inline-block size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent', className)} />
}

export const difficultyTone = { easy: 'ok', medium: 'warn', hard: 'bad' } as const

export function Waiting({ label }: { label: string }) {
  return <Card className="flex h-28 items-center justify-center gap-2 text-sm text-faint"><Spinner />{label}</Card>
}

export function Mono({ children, className }: { children: ReactNode; className?: string }) {
  return <code className={clsx('font-mono text-[12.5px]', className)}>{children}</code>
}

export function formatJson(v: unknown, max = 160): string {
  const s = JSON.stringify(v)
  if (s === undefined) return '—'
  return s.length > max ? s.slice(0, max) + '…' : s
}
