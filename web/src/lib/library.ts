import { useEffect, useState } from 'react'
import { getJson } from './api'
import type { LibraryProblem } from './types'

let cached: Promise<LibraryProblem[]> | null = null

/** The built-in example problems (recorded, so they open instantly). */
export function useLibrary() {
  const [data, setData] = useState<LibraryProblem[] | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    cached ??= getJson<LibraryProblem[]>('/api/problems')
    cached.then(setData).catch(() => { cached = null; setError(true) })
  }, [])
  return { data, error }
}
