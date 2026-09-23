// Main-thread side of the Pyodide sandbox.
//
// Jobs run one at a time. Python can't be interrupted from outside without cross-origin
// isolation, so a runaway job is handled by terminating the worker and booting a fresh one.
// Progress events the harness streamed before the kill are returned so the backend can
// still report which test case hung and which finished.

import { apiUrl } from '../lib/api'

export interface ExecReply {
  result?: unknown
  timed_out?: boolean
  events?: unknown[]
}

export type SandboxStatus = 'cold' | 'loading' | 'ready' | 'busy' | 'error'

interface Pending {
  id: number
  job: Record<string, unknown>
  timeoutS: number
  resolve: (r: ExecReply) => void
  events: unknown[]
  timer?: ReturnType<typeof setTimeout>
}

export class Sandbox {
  private worker: Worker | null = null
  private ready: Promise<void> | null = null
  private queue: Pending[] = []
  private current: Pending | null = null
  private nextId = 1
  private listeners = new Set<(s: SandboxStatus) => void>()
  status: SandboxStatus = 'cold'

  onStatus(fn: (s: SandboxStatus) => void) {
    this.listeners.add(fn)
    fn(this.status)
    return () => void this.listeners.delete(fn)
  }

  private setStatus(s: SandboxStatus) {
    this.status = s
    this.listeners.forEach((fn) => fn(s))
  }

  /** Boot Pyodide ahead of time so the first run doesn't pay the ~3-5s load. */
  warmUp(): Promise<void> {
    if (this.ready) return this.ready
    this.setStatus('loading')
    const worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' })
    this.worker = worker
    this.ready = new Promise<void>((resolve, reject) => {
      const onInit = (e: MessageEvent) => {
        if (e.data.type === 'ready') {
          worker.removeEventListener('message', onInit)
          this.setStatus('ready')
          resolve()
        } else if (e.data.type === 'init_error') {
          this.setStatus('error')
          this.ready = null
          reject(new Error(e.data.message))
        }
      }
      worker.addEventListener('message', onInit)
    })
    worker.addEventListener('message', (e) => this.onMessage(e))
    worker.postMessage({ type: 'init', harnessUrl: apiUrl('/api/harness.py') })
    this.ready.catch(() => {})
    return this.ready
  }

  run(job: Record<string, unknown>, timeoutS: number): Promise<ExecReply> {
    return new Promise((resolve) => {
      this.queue.push({ id: this.nextId++, job, timeoutS, resolve, events: [] })
      void this.pump()
    })
  }

  private async pump() {
    if (this.current || !this.queue.length) return
    const job = this.queue.shift()!
    this.current = job
    try {
      await this.warmUp()
    } catch (err) {
      this.finish({ result: { ok: false, error: { type: 'SandboxError', message: `Python sandbox failed to load: ${err}`, where: [] } } })
      return
    }
    this.setStatus('busy')
    this.worker!.postMessage({ type: 'run', id: job.id, job: job.job })
  }

  private onMessage(e: MessageEvent) {
    const msg = e.data
    const job = this.current
    if (!job || msg.id !== job.id) return
    if (msg.type === 'started') {
      // The clock starts only once Python is actually running this job.
      job.timer = setTimeout(() => this.kill(), job.timeoutS * 1000)
    } else if (msg.type === 'event') {
      job.events.push(msg.ev)
    } else if (msg.type === 'result') {
      this.finish({ result: msg.result })
    }
  }

  private kill() {
    const job = this.current
    this.worker?.terminate()
    this.worker = null
    this.ready = null
    this.setStatus('cold')
    if (job) this.finish({ timed_out: true, events: job.events })
    void this.warmUp() // respawn in the background for the next job
  }

  private finish(reply: ExecReply) {
    const job = this.current
    if (!job) return
    clearTimeout(job.timer)
    this.current = null
    if (this.status === 'busy') this.setStatus('ready')
    job.resolve(reply)
    void this.pump()
  }
}

export const sandbox = new Sandbox()
