import { useEffect, useState } from 'react'
import { getJson } from './api'

export type RoadmapId = 'blind75' | 'neetcode150'

export interface RoadmapProblem {
  id: string
  number: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  kind: 'function' | 'design' | 'special'
  entry?: string
  params?: string[]
  class_name?: string
  roadmaps: RoadmapId[]
  premium: boolean
  url: string
  recorded: boolean
}

export interface Roadmaps {
  roadmaps: { id: RoadmapId; title: string; source: string; source_url: string }[]
  categories: string[]
  problems: RoadmapProblem[]
}

let cached: Promise<Roadmaps> | null = null

export function useRoadmaps() {
  const [data, setData] = useState<Roadmaps | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    cached ??= getJson<Roadmaps>('/api/roadmaps')
    cached.then(setData).catch((e) => { cached = null; setError(String(e)) })
  }, [])
  return { data, error }
}

export const supported = (p: RoadmapProblem) => p.kind !== 'special'

/** Problems of one roadmap, in study order (category order, then list order). */
export function roadmapProblems(data: Roadmaps, id: RoadmapId): RoadmapProblem[] {
  return data.problems.filter((p) => p.roadmaps.includes(id))
}

/** The next problem after ``current`` in the same roadmap that a learner can open. */
export function nextInRoadmap(data: Roadmaps, id: RoadmapId, current: string): RoadmapProblem | undefined {
  const list = roadmapProblems(data, id).filter(supported)
  const i = list.findIndex((p) => p.id === current)
  return i >= 0 ? list[i + 1] : undefined
}
