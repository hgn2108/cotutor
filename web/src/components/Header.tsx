import { KeyRound, Monitor, Moon, Settings, Sun, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { Theme } from '../lib/prefs'
import type { Features } from '../lib/types'
import type { SandboxStatus } from '../sandbox/sandbox'
import { Badge } from './ui'

interface Props {
  sandboxStatus: SandboxStatus
  connected: boolean
  features: Features | null
  theme: Theme
  setTheme: (t: Theme) => void
  apiKey: string
  setApiKey: (k: string) => void
  onHome: () => void
}

const sandboxLabel: Record<SandboxStatus, [string, 'ok' | 'warn' | 'bad' | 'neutral']> = {
  cold: ['Python sandbox idle', 'neutral'],
  loading: ['Loading Python…', 'warn'],
  ready: ['Python ready', 'ok'],
  busy: ['Running code', 'ok'],
  error: ['Sandbox failed', 'bad'],
}

export function Header(p: Props) {
  const [open, setOpen] = useState(false)
  const panel = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (!panel.current?.contains(e.target as Node)) setOpen(false) }
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [open])

  const [label, tone] = sandboxLabel[p.sandboxStatus]
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:px-6">
        <button onClick={p.onHome} className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="size-7" />
          <span className="text-[15px] font-semibold tracking-tight">Cotutor</span>
        </button>
        <span className="hidden text-sm text-faint md:inline">Solve · verify · visualize</span>
        <div className="ml-auto flex items-center gap-2">
          <Badge tone={tone} className="hidden sm:inline-flex" title="Code runs locally in your browser via Pyodide (WebAssembly)">
            <span className="size-1.5 rounded-full bg-current" />{label}
          </Badge>
          {!p.connected && <Badge tone="bad">Server offline</Badge>}
          <a href="https://github.com/hgn2108/cotutor" target="_blank" rel="noreferrer" className="rounded-lg p-2 text-muted hover:bg-sunken hover:text-ink" aria-label="GitHub">
            <GithubMark />
          </a>
          <div className="relative" ref={panel}>
            <button onClick={() => setOpen((o) => !o)} className="rounded-lg p-2 text-muted hover:bg-sunken hover:text-ink" aria-label="Settings">
              <Settings className="size-4" />
            </button>
            {open && (
              <div className="absolute right-0 top-11 w-[min(340px,calc(100vw-2rem))] rounded-xl border border-line bg-panel p-4 shadow-xl">
                <div className="mb-4 flex items-center justify-between">
                  <span className="text-sm font-semibold">Settings</span>
                  <button onClick={() => setOpen(false)} className="text-muted hover:text-ink"><X className="size-4" /></button>
                </div>
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted"><KeyRound className="size-3.5" />Your Gemini API key (optional)</label>
                <input
                  type="password" value={p.apiKey} onChange={(e) => p.setApiKey(e.target.value)}
                  placeholder={p.features?.server_key ? 'Using the shared server key' : 'Required: no server key configured'}
                  className="w-full rounded-lg border border-line bg-sunken px-3 py-2 font-mono text-xs outline-none focus:border-accent"
                />
                <p className="mt-1.5 text-[11px] leading-4 text-faint">
                  Free from <a className="underline" href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">Google AI Studio</a>. Kept in this browser only and sent to the server just for your runs; lifts the shared hourly limit.
                </p>
                <div className="mt-4 mb-1.5 text-xs font-medium text-muted">Theme</div>
                <div className="grid grid-cols-3 gap-1 rounded-lg bg-sunken p-1">
                  {([['light', Sun], ['system', Monitor], ['dark', Moon]] as const).map(([t, Icon]) => (
                    <button key={t} onClick={() => p.setTheme(t)} className={`flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs capitalize ${p.theme === t ? 'bg-panel text-ink shadow-sm' : 'text-muted'}`}>
                      <Icon className="size-3.5" />{t}
                    </button>
                  ))}
                </div>
                {p.features && (
                  <p className="mt-4 text-[11px] text-faint">Models: {p.features.models.smart} · {p.features.models.fast}</p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

// Brand icons were removed from lucide; inline the GitHub mark.
function GithubMark() {
  return (
    <svg viewBox="0 0 16 16" className="size-4" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}
