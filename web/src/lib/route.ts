import { useCallback, useEffect, useState } from 'react'

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
