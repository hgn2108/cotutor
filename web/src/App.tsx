import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Header } from './components/Header'
import type { LearnMode } from './components/ModeToggle'
import { Home } from './features/home/Home'
import type { RoadmapLink } from './features/lesson/context'
import { RoadmapsPage } from './features/roadmaps/RoadmapsPage'
import { RunPage } from './features/run/RunPage'
import { useLibrary } from './lib/library'
import { usePref, useTheme } from './lib/prefs'
import { useProgress } from './lib/progress'
import { findByTitle, nextInRoadmap, type RoadmapId, type RoadmapProblem, useRoadmaps } from './lib/roadmaps'
import { type LessonRoute, lessonPath, parseLesson, useHashRoute } from './lib/route'
import type { LibraryProblem } from './lib/types'
import { useRun } from './lib/useRun'
import { sandbox, type SandboxStatus } from './sandbox/sandbox'

const LEAVE_WARNING = 'Leave this lesson? Your answers so far will be lost.'

export default function App() {
  const { theme, setTheme, dark } = useTheme()
  const [apiKey, setApiKey] = usePref('cotutor.geminiKey', '')
  const [mode, setMode] = usePref('cotutor.mode', 'guided') as [LearnMode, (m: LearnMode) => void]
  const [draft, setDraft] = usePref('cotutor.draft', '')
  const { state, features, connected, solve, cancel, reset } = useRun()
  const [sandboxStatus, setSandboxStatus] = useState<SandboxStatus>('cold')
  const [runId, setRunId] = useState(0)
  const [path, navigate] = useHashRoute()
  const roadmaps = useRoadmaps()
  const library = useLibrary()
  const { progress, record, importFrom } = useProgress()
  useEffect(() => sandbox.onStatus(setSandboxStatus), [])

  const roadmapRoute = path.match(/^\/roadmaps(?:\/(blind75|neetcode150))?$/)
  const lesson = parseLesson(path)
  const [lastRoadmap, setLastRoadmap] = usePref('cotutor.roadmap', 'blind75') as [RoadmapId, (r: RoadmapId) => void]
  const currentRoadmap = (roadmapRoute?.[1] as RoadmapId | undefined) ?? lastRoadmap

  // The URL of the lesson currently loaded, so Back/Forward/refresh can tell when it changed.
  const loadedPath = useRef<string | null>(null)
  // True while a guided lesson has answers that leaving would throw away.
  const dirty = useRef(false)
  const confirmLeave = useCallback(() => !dirty.current || window.confirm(LEAVE_WARNING), [])

  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => { if (dirty.current) e.preventDefault() }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [])

  const run = useCallback((route: LessonRoute, problem: string, opts: { fresh?: boolean; ref?: string } = {}) => {
    const to = lessonPath(route)
    loadedPath.current = to
    dirty.current = false
    setRunId((n) => n + 1) // remounts the lesson so progress starts fresh
    window.scrollTo({ top: 0 })
    navigate(to)
    void solve(problem, { apiKey: apiKey || undefined, ...opts })
  }, [solve, apiKey, navigate])

  const startCustom = useCallback((problem: string, fresh = false) => {
    setDraft(problem)
    run({ kind: 'custom' }, problem, { fresh })
  }, [run, setDraft])

  const startLibrary = useCallback((p: LibraryProblem, fresh = false) => {
    run({ kind: 'library', id: p.id }, p.statement, { fresh })
  }, [run])

  const startRoadmap = useCallback((item: RoadmapProblem, roadmap: RoadmapId, fresh = false) => {
    run({ kind: 'roadmap', roadmap, ref: item.id }, `LeetCode ${item.number}: ${item.title}`, { fresh, ref: item.id })
  }, [run])

  // Leaving a lesson route (Back button, a link, a typed URL) ends the run.
  // Arriving at one that isn't loaded (refresh, deep link, Forward) starts it.
  useEffect(() => {
    if (!lesson) {
      if (state.status === 'running') cancel()
      if (state.status !== 'idle') reset()
      loadedPath.current = null
      dirty.current = false
      return
    }
    if (loadedPath.current === path) return
    if (lesson.kind === 'roadmap') {
      if (!roadmaps.data) return
      const item = roadmaps.data.problems.find((p) => p.id === lesson.ref)
      if (item) startRoadmap(item, lesson.roadmap)
      else navigate(`/roadmaps/${lesson.roadmap}`)
    } else if (lesson.kind === 'library') {
      if (!library.data && !library.error) return
      const p = library.data?.find((x) => x.id === lesson.id)
      if (p) startLibrary(p)
      else navigate('/')
    } else {
      navigate('/') // a pasted problem isn't in the URL; its text is kept as a draft on the home page
    }
  }, [path, roadmaps.data, library.data, library.error]) // eslint-disable-line react-hooks/exhaustive-deps

  // A pasted problem that verified doesn't need to stay in the box.
  useEffect(() => {
    if (lesson?.kind === 'custom' && state.status === 'done' && state.summary?.verified && state.problem === draft) setDraft('')
  }, [state.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const origin = useMemo(() => {
    if (lesson?.kind !== 'roadmap' || !roadmaps.data) return null
    const item = roadmaps.data.problems.find((p) => p.id === lesson.ref)
    return item ? { roadmap: lesson.roadmap, item } : null
  }, [path, roadmaps.data]) // eslint-disable-line react-hooks/exhaustive-deps

  const goRoadmap = useCallback((id: RoadmapId) => {
    if (!confirmLeave()) return
    setLastRoadmap(id)
    navigate(`/roadmaps/${id}`)
  }, [navigate, setLastRoadmap, confirmLeave])

  const goHome = useCallback(() => {
    if (!confirmLeave()) return
    navigate('/')
  }, [navigate, confirmLeave])

  /** Open a suggested problem: from the roadmap when we know it (instant if recorded), else a fresh run. */
  const practice = useCallback((title: string) => {
    if (!confirmLeave()) return
    const item = roadmaps.data && findByTitle(roadmaps.data, title)
    if (item) startRoadmap(item, origin?.roadmap ?? (item.roadmaps.includes(lastRoadmap) ? lastRoadmap : item.roadmaps[0]))
    else startCustom(`LeetCode problem: ${title}`)
  }, [roadmaps.data, origin, lastRoadmap, startRoadmap, startCustom, confirmLeave])

  const roadmapLink: RoadmapLink | undefined = useMemo(() => {
    if (!origin) return undefined
    const next = roadmaps.data ? nextInRoadmap(roadmaps.data, origin.roadmap, origin.item.id) : undefined
    return {
      title: origin.item.title,
      url: origin.item.url,
      back: () => goRoadmap(origin.roadmap),
      next: next && { title: next.title, start: () => { if (confirmLeave()) startRoadmap(next, origin.roadmap) } },
    }
  }, [origin, roadmaps.data, goRoadmap, startRoadmap, confirmLeave])

  const onComplete = useCallback((score: number | null, lessonMode: 'guided' | 'walkthrough') => {
    dirty.current = false
    if (origin) record(origin.item.id, score, lessonMode)
  }, [origin, record])

  const retry = useCallback(() => {
    if (origin) startRoadmap(origin.item, origin.roadmap)
    else if (lesson?.kind === 'library') {
      const p = library.data?.find((x) => x.id === lesson.id)
      if (p) startLibrary(p)
    } else startCustom(state.problem)
  }, [origin, lesson, library.data, startRoadmap, startLibrary, startCustom, state.problem])

  const regenerate = useCallback(() => {
    if (origin) startRoadmap(origin.item, origin.roadmap, true)
    else if (lesson?.kind === 'library') {
      const p = library.data?.find((x) => x.id === lesson.id)
      if (p) startLibrary(p, true)
    } else startCustom(state.problem, true)
  }, [origin, lesson, library.data, startRoadmap, startLibrary, startCustom, state.problem])

  let page
  if (lesson) {
    page = (
      <RunPage
        state={state} runId={runId} mode={mode} setMode={setMode} dark={dark} onPractice={practice}
        onRetry={retry} onRegenerate={regenerate} onCancel={cancel}
        onBack={origin ? () => goRoadmap(origin.roadmap) : goHome}
        onBrowse={() => goRoadmap(origin?.roadmap ?? currentRoadmap)}
        roadmap={roadmapLink} onComplete={onComplete} onDirty={(d) => { dirty.current = d }}
      />
    )
  } else if (roadmapRoute) {
    page = (
      <RoadmapsPage
        data={roadmaps.data} error={roadmaps.error} roadmap={currentRoadmap}
        setRoadmap={(id) => { setLastRoadmap(id); navigate(`/roadmaps/${id}`) }}
        progress={progress} importProgress={importFrom} onStart={(item) => startRoadmap(item, currentRoadmap)}
        mode={mode} setMode={setMode}
      />
    )
  } else {
    page = (
      <Home mode={mode} setMode={setMode} draft={draft} setDraft={setDraft} onSolve={startCustom}
        library={library.data} libraryError={library.error} onLibrary={startLibrary} onRoadmap={goRoadmap}
        progress={progress} roadmaps={roadmaps.data} />
    )
  }

  return (
    <div className="min-h-full">
      <Header
        sandboxStatus={sandboxStatus} connected={connected} features={features} theme={theme} setTheme={setTheme}
        apiKey={apiKey} setApiKey={setApiKey} onHome={goHome}
        onRoadmaps={() => goRoadmap(currentRoadmap)} onRoadmapsPage={!!roadmapRoute}
      />
      {page}
    </div>
  )
}
