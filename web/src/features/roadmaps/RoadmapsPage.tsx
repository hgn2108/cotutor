import clsx from 'clsx'
import { Check, ChevronDown, Clock, Download, ExternalLink, Lock, Play, RotateCcw, Search, Upload, Zap } from 'lucide-react'
import { type ReactNode, useMemo, useRef, useState } from 'react'
import { Badge, Button, Card, difficultyTone, Spinner } from '../../components/ui'
import { downloadProgress, type ItemStatus, parseProgress, type Progress, statusOf } from '../../lib/progress'
import { type RoadmapId, type RoadmapProblem, roadmapProblems, type Roadmaps, supported } from '../../lib/roadmaps'

interface Props {
  data: Roadmaps | null
  error: string | null
  roadmap: RoadmapId
  setRoadmap: (id: RoadmapId) => void
  progress: Progress
  importProgress: (p: Progress) => void
  onStart: (item: RoadmapProblem) => void
}

type Filter = 'all' | ItemStatus
const FILTERS: [Filter, string][] = [['all', 'All'], ['new', 'Not started'], ['due', 'Due for review'], ['learned', 'Learned']]

export function RoadmapsPage({ data, error, roadmap, setRoadmap, progress, importProgress, onStart }: Props) {
  const [filter, setFilter] = useState<Filter>('all')
  const [difficulty, setDifficulty] = useState<'all' | RoadmapProblem['difficulty']>('all')
  const [query, setQuery] = useState('')
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const fileInput = useRef<HTMLInputElement>(null)
  const [importMsg, setImportMsg] = useState<string | null>(null)

  const problems = useMemo(() => (data ? roadmapProblems(data, roadmap) : []), [data, roadmap])
  if (error) return <Shell><Card className="p-5 text-sm text-bad">Couldn't load roadmaps: {error}</Card></Shell>
  if (!data) return <Shell><div className="flex h-40 items-center justify-center gap-2 text-sm text-faint"><Spinner />Loading roadmaps…</div></Shell>

  const meta = data.roadmaps.find((r) => r.id === roadmap)!
  const open = problems.filter(supported)
  const status = (p: RoadmapProblem) => statusOf(progress, p.id)
  const learned = open.filter((p) => status(p) !== 'new').length
  const due = open.filter((p) => status(p) === 'due')
  const next = open.find((p) => status(p) === 'new')
  const q = query.trim().toLowerCase()
  const visible = problems.filter((p) =>
    (filter === 'all' || (supported(p) && status(p) === filter))
    && (difficulty === 'all' || p.difficulty === difficulty)
    && (!q || p.title.toLowerCase().includes(q) || String(p.number) === q))

  const onImport = async (file: File) => {
    const parsed = parseProgress(await file.text())
    if (!parsed) return setImportMsg("That file isn't a Cotutor progress export.")
    importProgress(parsed)
    setImportMsg(`Imported progress for ${Object.keys(parsed.items).length} problems.`)
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight">Roadmaps</h1>
          <p className="mt-1 max-w-2xl text-[14px] leading-relaxed text-muted">
            Work through a curated list pattern by pattern. Each lesson starts from the problem's name, is verified before it teaches, and links to LeetCode so you can submit your own solution there.
          </p>
        </div>
        <div className="flex gap-1">
          <Button variant="ghost" className="text-xs" onClick={() => downloadProgress(progress)} title="Save your progress to a file (move it to another browser or device)"><Download className="size-3.5" />Export</Button>
          <Button variant="ghost" className="text-xs" onClick={() => fileInput.current?.click()}><Upload className="size-3.5" />Import</Button>
          <input ref={fileInput} type="file" accept="application/json" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) void onImport(f); e.target.value = '' }} />
        </div>
      </div>
      {importMsg && <p className="mt-2 text-xs text-muted">{importMsg}</p>}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl bg-sunken p-1">
          {data.roadmaps.map((r) => (
            <button key={r.id} onClick={() => setRoadmap(r.id)}
              className={clsx('rounded-lg px-4 py-1.5 text-sm font-medium transition', roadmap === r.id ? 'bg-panel text-ink shadow-sm' : 'text-muted hover:text-ink')}>
              {r.title}
            </button>
          ))}
        </div>
        <a href={meta.source_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-muted hover:text-ink">
          List: {meta.source} <ExternalLink className="size-3" />
        </a>
      </div>

      <Card className="mt-4 p-5">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <div className="min-w-[220px] flex-1">
            <div className="flex items-baseline justify-between text-sm">
              <span className="font-medium">{learned} of {open.length} learned</span>
              <span className="text-xs text-faint">{problems.length - open.length} coming soon</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-sunken">
              <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${(learned / Math.max(1, open.length)) * 100}%` }} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {due.length > 0 && (
              <Button variant="outline" onClick={() => onStart(due[0])}><RotateCcw className="size-3.5" />Review due ({due.length})</Button>
            )}
            {next && <Button onClick={() => onStart(next)}><Play className="size-3.5" />{learned ? 'Continue' : 'Start'}: {next.title}</Button>}
          </div>
        </div>
      </Card>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <div className="flex rounded-lg bg-sunken p-0.5 text-xs">
          {FILTERS.map(([f, label]) => (
            <button key={f} onClick={() => setFilter(f)} className={clsx('rounded-md px-2.5 py-1', filter === f ? 'bg-panel text-ink shadow-sm' : 'text-muted')}>{label}</button>
          ))}
        </div>
        <div className="flex rounded-lg bg-sunken p-0.5 text-xs">
          {(['all', 'easy', 'medium', 'hard'] as const).map((d) => (
            <button key={d} onClick={() => setDifficulty(d)} className={clsx('rounded-md px-2.5 py-1 capitalize', difficulty === d ? 'bg-panel text-ink shadow-sm' : 'text-muted')}>{d === 'all' ? 'Any difficulty' : d}</button>
          ))}
        </div>
        <label className="ml-auto flex items-center gap-2 rounded-lg border border-line bg-panel px-2.5 py-1.5 text-xs focus-within:border-accent">
          <Search className="size-3.5 text-faint" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search title or number" className="w-44 bg-transparent outline-none placeholder:text-faint" />
        </label>
      </div>

      <div className="mt-4 grid gap-3">
        {data.categories.map((cat) => {
          const all = problems.filter((p) => p.category === cat)
          const rows = visible.filter((p) => p.category === cat)
          if (!all.length || !rows.length) return null
          const catOpen = all.filter(supported)
          const catLearned = catOpen.filter((p) => status(p) !== 'new').length
          const isCollapsed = collapsed.has(cat)
          return (
            <Card key={cat} className="overflow-hidden">
              <button onClick={() => setCollapsed((c) => { const n = new Set(c); if (n.has(cat)) n.delete(cat); else n.add(cat); return n })}
                className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-sunken/50">
                <ChevronDown className={clsx('size-4 text-faint transition', isCollapsed && '-rotate-90')} />
                <span className="text-[14px] font-semibold">{cat}</span>
                <span className="font-mono text-[11px] text-faint">{catLearned}/{catOpen.length}</span>
                <div className="ml-auto h-1.5 w-24 overflow-hidden rounded-full bg-sunken">
                  <div className="h-full rounded-full bg-ok" style={{ width: `${(catLearned / Math.max(1, catOpen.length)) * 100}%` }} />
                </div>
              </button>
              {!isCollapsed && (
                <ul className="border-t border-line">
                  {rows.map((p) => <Row key={p.id} p={p} status={status(p)} onStart={onStart} />)}
                </ul>
              )}
            </Card>
          )
        })}
        {!visible.length && <p className="py-8 text-center text-sm text-faint">No problems match these filters.</p>}
      </div>
      <p className="mt-6 text-center text-[11.5px] leading-relaxed text-faint">
        Progress is saved in this browser only. Lesson content is generated and verified by Cotutor; problem statements belong to LeetCode.<br />
        Design problems (e.g. LRU Cache) and a few with special node structures are coming soon.
      </p>
    </Shell>
  )
}

function Shell({ children }: { children: ReactNode }) {
  return <main className="mx-auto max-w-4xl px-4 pb-20 pt-8 sm:px-6">{children}</main>
}

function Row({ p, status, onStart }: { p: RoadmapProblem; status: ItemStatus; onStart: (p: RoadmapProblem) => void }) {
  const ok = supported(p)
  return (
    <li className="flex items-center gap-3 border-b border-line px-4 py-2.5 last:border-0">
      <StatusIcon status={ok ? status : 'locked'} />
      <span className="w-11 shrink-0 font-mono text-[11.5px] text-faint">#{p.number}</span>
      <span className={clsx('min-w-0 flex-1 truncate text-[13.5px]', ok ? 'text-ink' : 'text-faint')}>{p.title}</span>
      <div className="hidden items-center gap-1 sm:flex">
        <Badge tone={difficultyTone[p.difficulty]}>{p.difficulty}</Badge>
        {p.premium && <Badge title="LeetCode Premium problem; the lesson still works from its name">premium</Badge>}
        {ok && p.recorded && <Badge tone="accent" title="Already recorded: opens instantly"><Zap className="size-3" />instant</Badge>}
      </div>
      {ok ? (
        <Button variant={status === 'due' ? 'primary' : 'outline'} className="px-2.5 py-1 text-xs" onClick={() => onStart(p)}>
          {status === 'new' ? 'Learn' : status === 'due' ? 'Review' : 'Revisit'}
        </Button>
      ) : (
        <span className="w-[62px] text-right text-[11px] text-faint" title={p.kind === 'design' ? 'Design problems (a class with several methods) are coming soon' : 'Needs node structures not supported yet'}>soon</span>
      )}
      <a href={p.url} target="_blank" rel="noreferrer" className="rounded p-1 text-faint hover:text-ink" aria-label={`${p.title} on LeetCode`} title="Open on LeetCode">
        <ExternalLink className="size-3.5" />
      </a>
    </li>
  )
}

function StatusIcon({ status }: { status: ItemStatus | 'locked' }) {
  const base = 'flex size-5 shrink-0 items-center justify-center rounded-full'
  if (status === 'learned') return <span className={clsx(base, 'bg-ok-soft text-ok')} title="Learned"><Check className="size-3" strokeWidth={3} /></span>
  if (status === 'due') return <span className={clsx(base, 'bg-warn-soft text-warn')} title="Due for review"><Clock className="size-3" /></span>
  if (status === 'locked') return <span className={clsx(base, 'bg-sunken text-faint')} title="Coming soon"><Lock className="size-2.5" /></span>
  return <span className={clsx(base, 'border border-line')} title="Not started" />
}
