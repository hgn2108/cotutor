import { createContext, useContext } from 'react'
import type { RunState } from '../../lib/useRun'

export type ChapterId = 'problem' | 'pattern' | 'brute' | 'bottleneck' | 'insight' | 'watch' | 'complexity' | 'edges' | 'recap'

export interface Score { correct: number; total: number }

/** Set when the lesson was opened from a roadmap. */
export interface RoadmapLink {
  title: string
  url: string
  next?: { title: string; start: () => void }
  back: () => void
}

export interface LessonCtx {
  state: RunState
  guided: boolean
  isDone: (id: ChapterId) => boolean
  complete: (id: ChapterId) => void
  record: (id: ChapterId, score: Score) => void
  scores: Partial<Record<ChapterId, Score>>
  onSolve: (problem: string) => void
  dark: boolean
  roadmap?: RoadmapLink
  /** Mark the lesson finished: guided mode reports a score, walkthrough reports null. */
  finish: (score: number | null) => void
  finished: boolean
}

export const LessonContext = createContext<LessonCtx | null>(null)

export function useLesson(): LessonCtx {
  const ctx = useContext(LessonContext)
  if (!ctx) throw new Error('useLesson must be used inside <Lesson>')
  return ctx
}
