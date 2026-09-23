/// <reference lib="webworker" />
// Runs untrusted Python (model- or user-written) inside Pyodide, isolated in a Web Worker.
// The same harness.py the backend uses for evals is fetched from the API and imported here.

export const PYODIDE_VERSION = '314.0.7'
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

type PyProxy = { run_job_json: (job: string, emit: (ev: string) => void) => string }

let harness: PyProxy | null = null

async function init(harnessUrl: string) {
  const { loadPyodide } = await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)
  const [pyodide, source] = await Promise.all([
    loadPyodide({ indexURL: PYODIDE_URL }),
    fetch(harnessUrl).then((r) => {
      if (!r.ok) throw new Error(`Could not load harness (${r.status})`)
      return r.text()
    }),
  ])
  pyodide.FS.writeFile('/home/pyodide/harness.py', source)
  pyodide.runPython('import sys; sys.path.insert(0, "/home/pyodide"); sys.setrecursionlimit(3000)')
  harness = pyodide.pyimport('harness') as PyProxy
}

self.onmessage = async (e: MessageEvent) => {
  const msg = e.data
  if (msg.type === 'init') {
    try {
      await init(msg.harnessUrl)
      self.postMessage({ type: 'ready' })
    } catch (err) {
      self.postMessage({ type: 'init_error', message: String(err) })
    }
    return
  }
  if (msg.type === 'run') {
    if (!harness) {
      self.postMessage({ type: 'result', id: msg.id, result: { ok: false, error: { type: 'SandboxError', message: 'Sandbox not ready', where: [] } } })
      return
    }
    self.postMessage({ type: 'started', id: msg.id })
    const emit = (ev: string) => self.postMessage({ type: 'event', id: msg.id, ev: JSON.parse(ev) })
    try {
      const out = harness.run_job_json(JSON.stringify(msg.job), emit)
      self.postMessage({ type: 'result', id: msg.id, result: JSON.parse(out) })
    } catch (err) {
      // e.g. a RecursionError that escaped, or a Wasm stack overflow
      self.postMessage({ type: 'result', id: msg.id, result: { ok: false, error: { type: 'Crash', message: String(err).slice(0, 400), where: [] } } })
    }
  }
}
