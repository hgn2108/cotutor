import { useCallback, useEffect, useMemo, useState } from 'react'
import { Header } from './components/Header'
import type { LearnMode } from './components/ModeToggle'
import { Home } from './features/home/Home'
import type { RoadmapLink } from './features/lesson/context'
import { RoadmapsPage } from './features/roadmaps/RoadmapsPage'
import { RunPage } from './features/run/RunPage'
import { usePref, useTheme } from './lib/prefs'
import { useProgress } from './lib/progress'
import { nextInRoadmap, type RoadmapId, type RoadmapProblem, useRoadmaps } from './lib/roadmaps'
import { useHashRoute } from './lib/route'
import { useRun } from './lib/useRun'
import { sandbox, type SandboxStatus } from './sandbox/sandbox'

interface Origin { roadmap: RoadmapId; item: RoadmapProblem }

export default function App() {
  const { theme, setTheme, dark } = useTheme()
  const [apiKey, setApiKey] = usePref('cotutor.geminiKey', '')
  const [mode, setMode] = usePref('cotutor.mode', 'guided') as [LearnMode, (m: LearnMode) => void]
  const { state, features, connected, solve, cancel, reset } = useRun()
  const [sandboxStatus, setSandboxStatus] = useState<SandboxStatus>('cold')
  const [runId, setRunId] = useState(0)
  const [origin, setOrigin] = useState<Origin | null>(null)
  const [path, navigate] = useHashRoute()
  const roadmaps = useRoadmaps()
  const { progress, record, importFrom } = useProgress()
  useEffect(() => sandbox.onStatus(setSandboxStatus), [])

  const roadmapRoute = path.match(/^\/roadmaps(?:\/(blind75|neetcode150))?$/)
  const [lastRoadmap, setLastRoadmap] = usePref('cotutor.roadmap', 'blind75') as [RoadmapId, (r: RoadmapId) => void]
  const currentRoadmap = (roadmapRoute?.[1] as RoadmapId | undefined) ?? lastRoadmap

  const run = useCallback((problem: string, opts: { fresh?: boolean; ref?: string } = {}) => {
    setRunId((n) => n + 1) // remounts the lesson so progress starts fresh
    window.scrollTo({ top: 0 })
    void solve(problem, { apiKey: apiKey || undefined, ...opts })
  }, [solve, apiKey])

  const start = useCallback((problem: string, fresh = false) => {
    setOrigin(null)
    run(problem, { fresh })
  }, [run])

  const startRoadmap = useCallback((item: RoadmapProblem, roadmap: RoadmapId, fresh = false) => {
    setOrigin({ roadmap, item })
    run(`LeetCode ${item.number}: ${item.title}`, { fresh, ref: item.id })
  }, [run])

  const goRoadmap = useCallback((id: RoadmapId) => {
    setLastRoadmap(id)
    reset()
    navigate(`/roadmaps/${id}`)
  }, [navigate, reset, setLastRoadmap])

  const goHome = useCallback(() => {
    reset()
    setOrigin(null)
    navigate('/')
  }, [navigate, reset])

  const roadmapLink: RoadmapLink | undefined = useMemo(() => {
    if (!origin) return undefined
    const next = roadmaps.data ? nextInRoadmap(roadmaps.data, origin.roadmap, origin.item.id) : undefined
    return {
      title: origin.item.title,
      url: origin.item.url,
      back: () => goRoadmap(origin.roadmap),
      next: next && { title: next.title, start: () => startRoadmap(next, origin.roadmap) },
    }
  }, [origin, roadmaps.data, goRoadmap, startRoadmap])

  const onComplete = useCallback((score: number | null, lessonMode: 'guided' | 'walkthrough') => {
    if (origin) record(origin.item.id, score, lessonMode)
  }, [origin, record])

  let page
  if (state.status !== 'idle') {
    page = (
      <RunPage
        state={state} runId={runId} mode={mode} setMode={setMode} dark={dark} onSolve={start}
        onRerun={() => (origin ? startRoadmap(origin.item, origin.roadmap, true) : start(state.problem, true))}
        onCancel={cancel} onBack={origin ? () => goRoadmap(origin.roadmap) : goHome}
        roadmap={roadmapLink} onComplete={onComplete}
      />
    )
  } else if (roadmapRoute) {
    page = (
      <RoadmapsPage
        data={roadmaps.data} error={roadmaps.error} roadmap={currentRoadmap}
        setRoadmap={(id) => { setLastRoadmap(id); navigate(`/roadmaps/${id}`) }}
        progress={progress} importProgress={importFrom} onStart={(item) => startRoadmap(item, currentRoadmap)}
      />
    )
  } else {
    page = <Home mode={mode} setMode={setMode} onSolve={start} onRoadmap={goRoadmap} />
  }

  return (
    <div className="min-h-full">
      <Header
        sandboxStatus={sandboxStatus} connected={connected} features={features} theme={theme} setTheme={setTheme}
        apiKey={apiKey} setApiKey={setApiKey} onHome={goHome}
        onRoadmaps={() => goRoadmap(currentRoadmap)} onRoadmapsPage={!!roadmapRoute && state.status === 'idle'}
      />
      {page}
    </div>
  )
}
