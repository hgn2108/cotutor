// Learning progress, kept in this browser only (no accounts). Spaced repetition decides when
// a learned problem is due for review: a strong lesson pushes the next review further out, a
// weak one brings it back tomorrow.

import { useCallback, useEffect, useState } from 'react'

const KEY = 'cotutor.progress.v1'
const DAY = 24 * 60 * 60 * 1000
export const REVIEW_INTERVALS_DAYS = [1, 3, 7, 16, 35]
const PASS = 0.7

export interface Attempt { at: number; score: number | null; mode: 'guided' | 'walkthrough' }
export interface ItemProgress { box: number; lastAt: number; nextDue: number; attempts: Attempt[] }
export interface Progress { version: 1; items: Record<string, ItemProgress> }
export type ItemStatus = 'new' | 'due' | 'learned'

export const emptyProgress = (): Progress => ({ version: 1, items: {} })

/** Record a finished lesson. ``score`` is the share of guided questions answered right. */
export function recordAttempt(p: Progress, id: string, attempt: Attempt): Progress {
  const prev = p.items[id]
  let box: number
  if (attempt.score === null) box = prev?.box ?? 0            // reading along doesn't promote
  else if (attempt.score >= PASS) box = prev ? Math.min(prev.box + 1, REVIEW_INTERVALS_DAYS.length - 1) : 1
  else box = 0
  const item: ItemProgress = {
    box, lastAt: attempt.at, nextDue: attempt.at + REVIEW_INTERVALS_DAYS[box] * DAY,
    attempts: [...(prev?.attempts ?? []), attempt].slice(-20),
  }
  return { ...p, items: { ...p.items, [id]: item } }
}

export function statusOf(p: Progress, id: string, now = Date.now()): ItemStatus {
  const item = p.items[id]
  if (!item) return 'new'
  return item.nextDue <= now ? 'due' : 'learned'
}

/** Merge an imported file into the current progress, keeping the most recent state per item. */
export function mergeProgress(a: Progress, b: Progress): Progress {
  const items = { ...a.items }
  for (const [id, item] of Object.entries(b.items)) {
    if (!items[id] || item.lastAt > items[id].lastAt) items[id] = item
  }
  return { version: 1, items }
}

export function parseProgress(text: string): Progress | null {
  try {
    const data = JSON.parse(text)
    if (data?.version !== 1 || typeof data.items !== 'object') return null
    return data as Progress
  } catch {
    return null
  }
}

function load(): Progress {
  try {
    return parseProgress(localStorage.getItem(KEY) ?? '') ?? emptyProgress()
  } catch {
    return emptyProgress()
  }
}

function save(p: Progress) {
  try {
    localStorage.setItem(KEY, JSON.stringify(p))
  } catch { /* storage unavailable (private mode): progress lasts for this session only */ }
}

export function useProgress() {
  const [progress, setProgress] = useState<Progress>(load)
  useEffect(() => save(progress), [progress])
  useEffect(() => {
    // Keep several open tabs in sync.
    const onStorage = (e: StorageEvent) => { if (e.key === KEY) setProgress(load()) }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])
  const record = useCallback((id: string, score: number | null, mode: Attempt['mode']) =>
    setProgress((p) => recordAttempt(p, id, { at: Date.now(), score, mode })), [])
  const importFrom = useCallback((incoming: Progress) => setProgress((p) => mergeProgress(p, incoming)), [])
  return { progress, record, importFrom }
}

export function downloadProgress(p: Progress) {
  const blob = new Blob([JSON.stringify(p, null, 1)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `cotutor-progress-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}
