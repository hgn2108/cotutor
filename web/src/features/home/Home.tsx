import { ArrowRight, FlaskConical, Gauge, MapIcon, Play, Search, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getJson } from '../../lib/api'
import type { LibraryProblem } from '../../lib/types'
import { type LearnMode, ModeToggle } from '../../components/ModeToggle'
import { Badge, Button, difficultyTone } from '../../components/ui'

interface Props {
  mode: LearnMode
  setMode: (m: LearnMode) => void
  onSolve: (problem: string) => void
  onRoadmap: (id: 'blind75' | 'neetcode150') => void
}

const pillars = [
  { icon: Search, title: 'Patterns, not answers', body: 'Learn which phrases in a problem point to which technique, so you recognize it next time.' },
  { icon: FlaskConical, title: 'Brute force → insight', body: 'Start from the obvious solution, find its wasted work yourself, then see how to remove it.' },
  { icon: Gauge, title: 'Big-O you can see', body: 'Count how often each line actually runs as n doubles, and derive the complexity line by line.' },
  { icon: ShieldCheck, title: 'Verified before taught', body: 'Every solution passes tests and hundreds of random inputs in a sandbox before you see it.' },
]

export function Home({ mode, setMode, onSolve, onRoadmap }: Props) {
  const [text, setText] = useState('')
  const [library, setLibrary] = useState<LibraryProblem[]>([])
  useEffect(() => { getJson<LibraryProblem[]>('/api/problems').then(setLibrary).catch(() => {}) }, [])

  const submit = () => text.trim().length >= 15 && onSolve(text.trim())

  return (
    <div className="mx-auto max-w-5xl px-4 pb-20 pt-10 sm:px-6 sm:pt-16">
      <div className="mx-auto max-w-3xl text-center">
        <Badge tone="accent" className="mb-5">Learn the reasoning behind coding problems</Badge>
        <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-[44px] sm:leading-[1.1]">
          Understand the algorithm, <span className="text-accent">not just the answer.</span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-pretty text-[15px] leading-relaxed text-muted">
          Paste any coding problem. Cotutor walks you from the wording to the pattern, from brute force to the insight,
          and shows you why the Big-O is what it is. Behind the scenes, agents verify every solution before teaching it.
        </p>
      </div>

      <div className="mx-auto mt-8 max-w-3xl rounded-2xl border border-line bg-panel p-2 shadow-sm focus-within:border-accent/60">
        <textarea
          value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }}
          rows={6}
          placeholder={'Paste a problem statement, e.g.\n\nGiven a string s, return the length of the longest substring without repeating characters.\nExample: s = "abcabcbb" -> 3'}
          className="w-full resize-none bg-transparent px-3 py-2.5 text-[14px] leading-relaxed outline-none placeholder:text-faint"
        />
        <div className="flex flex-wrap items-center gap-2 border-t border-line px-2 pt-2">
          <ModeToggle mode={mode} setMode={setMode} size="sm" />
          <span className="ml-auto hidden text-xs text-faint sm:inline">⌘ + Enter</span>
          <Button onClick={submit} disabled={text.trim().length < 15}><Play className="size-3.5" />{mode === 'guided' ? 'Start lesson' : 'Explain it'}</Button>
        </div>
      </div>

      <div className="mt-12">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold">Follow a roadmap</h2>
          <span className="text-xs text-faint">Progress and review reminders are saved in your browser</span>
        </div>
        <div className="grid gap-2.5 sm:grid-cols-2">
          {([['blind75', 'Blind 75', 'The classic interview shortlist, one problem per core pattern.'],
             ['neetcode150', 'NeetCode 150', 'Blind 75 plus 75 more, grouped into 18 patterns.']] as const).map(([id, title, body]) => (
            <button key={id} onClick={() => onRoadmap(id)} className="group rounded-xl border border-line bg-panel p-4 text-left transition hover:border-accent/50 hover:shadow-sm">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-[15px] font-semibold"><MapIcon className="size-4 text-accent" />{title}</span>
                <ArrowRight className="size-4 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent" />
              </div>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted">{body}</p>
            </button>
          ))}
        </div>
      </div>

      {library.length > 0 && (
        <div className="mt-12">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-sm font-semibold">Try a classic</h2>
            <span className="text-xs text-faint">Previously verified runs replay instantly</span>
          </div>
          <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {library.map((p) => (
              <button key={p.id} onClick={() => onSolve(p.statement)} className="group rounded-xl border border-line bg-panel p-3.5 text-left transition hover:border-accent/50 hover:shadow-sm">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-medium">{p.title}</span>
                  <ArrowRight className="size-4 shrink-0 text-faint transition group-hover:translate-x-0.5 group-hover:text-accent" />
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  <Badge tone={difficultyTone[p.difficulty]}>{p.difficulty}</Badge>
                  {mode === 'walkthrough' && p.tags.map((t) => <Badge key={t}>{t}</Badge>)}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-14 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {pillars.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-xl p-3">
            <Icon className="mb-2 size-5 text-accent" />
            <div className="text-sm font-medium">{title}</div>
            <p className="mt-1 text-[13px] leading-relaxed text-muted">{body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
