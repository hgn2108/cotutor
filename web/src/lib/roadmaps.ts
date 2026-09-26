import { useEffect, useState } from 'react'
import { getJson } from './api'

export type RoadmapId = 'blind75' | 'neetcode150'

export interface RoadmapProblem {
  id: string
  number: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  category: string
  kind: 'function' | 'design' | 'codec' | 'special'
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

const NUMBER_WORDS: Record<string, string> = {
  one: '1', two: '2', three: '3', four: '4', five: '5', six: '6', seven: '7', eight: '8', nine: '9', ten: '10',
}

/** Loose title key so "Three Sum" matches "3Sum" and "Two Sum II" matches "Two Sum II - Input Array Is Sorted". */
export function titleKey(title: string): string {
  return title.toLowerCase()
    .replace(/^leetcode\s*\d*[:.)-]?\s*/, '')
    .replace(/\b(one|two|three|four|five|six|seven|eight|nine|ten)\b/g, (w) => NUMBER_WORDS[w])
    .replace(/[^a-z0-9]/g, '')
}

/** Find a roadmap problem by a free-form title (e.g. a "similar problem" suggestion). */
export function findByTitle(data: Roadmaps, title: string): RoadmapProblem | undefined {
  const key = titleKey(title)
  if (!key) return undefined
  const open = data.problems.filter(supported)
  return open.find((p) => titleKey(p.title) === key)
    ?? open.find((p) => titleKey(p.title).startsWith(key) && key.length >= 6)
}
