import { useCallback, useEffect, useState } from 'react'
import type { RoadmapId } from './roadmaps'

/** Minimal hash routing so pages are linkable and survive a refresh on static hosting. */
export function useHashRoute(): [string, (path: string) => void] {
  const read = () => window.location.hash.replace(/^#/, '') || '/'
  const [path, setPath] = useState(read)
  useEffect(() => {
    const on = () => setPath(read())
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const navigate = useCallback((to: string) => {
    if (read() !== to) window.location.hash = to
    setPath(to)
  }, [])
  return [path, navigate]
}

/** Where a lesson came from. Roadmap and library lessons can be reopened from their URL. */
export type LessonRoute =
  | { kind: 'roadmap'; roadmap: RoadmapId; ref: string }
  | { kind: 'library'; id: string }
  | { kind: 'custom' }

export function lessonPath(r: LessonRoute): string {
  if (r.kind === 'roadmap') return `/learn/${r.roadmap}/${r.ref}`
  if (r.kind === 'library') return `/learn/library/${r.id}`
  return '/learn'
}

export function parseLesson(path: string): LessonRoute | null {
  const m = path.match(/^\/learn(?:\/([\w-]+)\/([\w-]+))?\/?$/)
  if (!m) return null
  if (!m[1]) return { kind: 'custom' }
  if (m[1] === 'library') return { kind: 'library', id: m[2] }
  if (m[1] === 'blind75' || m[1] === 'neetcode150') return { kind: 'roadmap', roadmap: m[1], ref: m[2] }
  return null
}
