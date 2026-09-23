import { useEffect, useState } from 'react'

// Per-browser conveniences. Storage can be unavailable (private mode), so every access is guarded.
function read(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback
  } catch {
    return fallback
  }
}

function write(key: string, value: string) {
  try {
    if (value) localStorage.setItem(key, value)
    else localStorage.removeItem(key)
  } catch {
    /* ignore */
  }
}

export function usePref(key: string, fallback: string) {
  const [value, setValue] = useState(() => read(key, fallback))
  useEffect(() => write(key, value), [key, value])
  return [value, setValue] as const
}

export type Theme = 'system' | 'light' | 'dark'

export function useTheme() {
  const [theme, setTheme] = usePref('cotutor.theme', 'system')
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const on = (e: MediaQueryListEvent) => setSystemDark(e.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  const dark = theme === 'dark' || (theme === 'system' && systemDark)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])
  return { theme: theme as Theme, setTheme: setTheme as (t: Theme) => void, dark }
}
