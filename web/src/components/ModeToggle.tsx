import clsx from 'clsx'
import { GraduationCap, ScrollText } from 'lucide-react'

export type LearnMode = 'guided' | 'walkthrough'

export function ModeToggle({ mode, setMode, size = 'md' }: { mode: LearnMode; setMode: (m: LearnMode) => void; size?: 'sm' | 'md' }) {
  const opts = [
    { id: 'guided' as const, label: 'Guided', icon: GraduationCap, title: 'Interactive: predict, answer and unlock one step at a time' },
    { id: 'walkthrough' as const, label: 'Walkthrough', icon: ScrollText, title: 'Read-only: every step revealed, no questions' },
  ]
  return (
    <div className="flex rounded-lg bg-sunken p-0.5">
      {opts.map(({ id, label, icon: Icon, title }) => (
        <button key={id} onClick={() => setMode(id)} title={title}
          className={clsx('flex items-center gap-1.5 rounded-md font-medium transition', size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-1.5 text-[13px]',
            mode === id ? 'bg-panel text-ink shadow-sm' : 'text-muted hover:text-ink')}>
          <Icon className="size-3.5" />{label}
        </button>
      ))}
    </div>
  )
}
