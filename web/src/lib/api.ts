const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? ''

export function apiUrl(path: string): string {
  return `${BASE}${path}`
}

export function wsUrl(path: string): string {
  const base = BASE || window.location.origin
  return base.replace(/^http/, 'ws') + path
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path))
  if (!res.ok) throw new Error(`${path}: ${res.status}`)
  return res.json() as Promise<T>
}
