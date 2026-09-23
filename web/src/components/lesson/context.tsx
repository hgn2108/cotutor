import { createContext, useContext } from 'react'
import type { RunState } from '../../lib/useRun'

export type ChapterId = 'problem' | 'pattern' | 'brute' | 'bottleneck' | 'insight' | 'watch' | 'complexity' | 'edges' | 'recap'

export interface Score { correct: number; total: number }

export interface LessonCtx {
  state: RunState
  guided: boolean
  isDone: (id: ChapterId) => boolean
  complete: (id: ChapterId) => void
  record: (id: ChapterId, score: Score) => void
  scores: Partial<Record<ChapterId, Score>>
  onSolve: (problem: string) => void
  dark: boolean
}

export const LessonContext = createContext<LessonCtx | null>(null)

export function useLesson(): LessonCtx {
  const ctx = useContext(LessonContext)
  if (!ctx) throw new Error('useLesson must be used inside <Lesson>')
  return ctx
}
