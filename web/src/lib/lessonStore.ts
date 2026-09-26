// A guided lesson's progress, kept for this browser tab so a refresh, the Back button or a
// detour to another page doesn't throw away the steps already done.

import type { ChapterId, Score } from '../features/lesson/context'

export interface SavedLesson {
  done: ChapterId[]
  scores: Partial<Record<ChapterId, Score>>
  finished: boolean
}

const PREFIX = 'cotutor.lesson:'

export function loadLesson(key: string): SavedLesson | null {
  try {
    const raw = sessionStorage.getItem(PREFIX + key)
    return raw ? (JSON.parse(raw) as SavedLesson) : null
  } catch {
    return null
  }
}

export function saveLesson(key: string, lesson: SavedLesson) {
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify(lesson))
  } catch { /* storage unavailable: progress lasts until the page is left */ }
}

export function clearLesson(key: string) {
  try {
    sessionStorage.removeItem(PREFIX + key)
  } catch { /* ignore */ }
}
