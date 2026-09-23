import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { sandbox } from '../sandbox/sandbox'
import { wsUrl } from './api'
import type {
  Complexity, DebugAttempt, Explanation, Features, LessonDeep, LessonIntro, LineCounts, ProblemSpec, ServerMessage, Solution, StageEvent,
  Summary, TestPlan, Trace, Verification,
} from './types'

export interface ExecLogEntry { id: string; kind: string; ms: number; outcome: 'ok' | 'timeout' | 'error' }

export interface RunState {
  status: 'idle' | 'running' | 'done' | 'error'
  problem: string
  stages: StageEvent[]
  spec?: ProblemSpec
  testPlan?: TestPlan
  oracle?: { trusted: boolean; has_checker: boolean }
  solutions: Solution[]
  verifications: Verification[]
  debugAttempts: DebugAttempt[]
  complexity?: Complexity
  explanation?: Explanation
  trace?: Trace
  lessonIntro?: LessonIntro
  lessonDeep?: LessonDeep
  lineCounts?: LineCounts
  summary?: Summary
  error?: { message: string; code?: string }
  execLog: ExecLogEntry[]
}

const initial: RunState = {
  status: 'idle', problem: '', stages: [], solutions: [], verifications: [], debugAttempts: [], execLog: [],
}

type Action =
  | { type: 'start'; problem: string }
  | { type: 'message'; msg: ServerMessage }
  | { type: 'exec'; entry: ExecLogEntry }
  | { type: 'fail'; message: string }
  | { type: 'reset' }
  | { type: 'disconnected' }

function reducer(state: RunState, action: Action): RunState {
  switch (action.type) {
    case 'start':
      return { ...initial, status: 'running', problem: action.problem }
    case 'reset':
      return initial
    case 'fail':
      return { ...state, status: 'error', error: { message: action.message } }
    case 'disconnected':
      return state.status === 'running' ? { ...state, status: 'error', error: { message: 'Lost connection to the server mid-run. It will reconnect; try again in a moment.' } } : state
    case 'exec':
      return { ...state, execLog: [...state.execLog, action.entry] }
    case 'message':
      return applyMessage(state, action.msg)
  }
}

function applyMessage(state: RunState, msg: ServerMessage): RunState {
  switch (msg.type) {
    case 'stage': {
      const i = state.stages.findIndex((s) => s.id === msg.id)
      const stages = i < 0 ? [...state.stages, msg] : state.stages.map((s, j) => (j === i ? msg : s))
      return { ...state, stages }
    }
    case 'artifact': {
      const d = msg.data as never
      switch (msg.name) {
        case 'spec': return { ...state, spec: d }
        case 'test_plan': return { ...state, testPlan: d }
        case 'oracle': return { ...state, oracle: d }
        case 'solution': return { ...state, solutions: [...state.solutions, d] }
        case 'verification': return { ...state, verifications: [...state.verifications, d] }
        case 'debug_attempt': return { ...state, debugAttempts: [...state.debugAttempts, d] }
        case 'complexity': return { ...state, complexity: d }
        case 'explanation': return { ...state, explanation: d }
        case 'trace': return { ...state, trace: d }
        case 'lesson_intro': return { ...state, lessonIntro: d }
        case 'lesson_deep': return { ...state, lessonDeep: d }
        case 'line_counts': return { ...state, lineCounts: d }
      }
      return state
    }
    case 'error':
      return { ...state, status: 'error', error: { message: msg.message, code: msg.code } }
    case 'done':
      return { ...state, status: state.status === 'error' ? 'error' : 'done', summary: msg.summary }
    default:
      return state
  }
}

export interface SolveOptions { solver: 'gemini' | 'llama'; apiKey?: string; fresh?: boolean }

export function useRun() {
  const [state, dispatch] = useReducer(reducer, initial)
  const [features, setFeatures] = useState<Features | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const openRef = useRef<Promise<WebSocket> | null>(null)
  const alive = useRef(true)
  const reconnect = useRef<() => void>(() => {})

  const connect = useCallback((): Promise<WebSocket> => {
    const existing = wsRef.current
    if (existing && existing.readyState === WebSocket.OPEN) return Promise.resolve(existing)
    if (openRef.current) return openRef.current
    const ws = new WebSocket(wsUrl('/api/session'))
    wsRef.current = ws
    const stale = () => wsRef.current !== ws // events from a socket we've already replaced
    const opening = new Promise<WebSocket>((resolve, reject) => {
      ws.onopen = () => { if (!stale()) { setConnected(true); resolve(ws) } }
      ws.onerror = () => reject(new Error('Could not connect to the Cotutor server.'))
      ws.onclose = () => {
        if (stale()) return
        setConnected(false)
        dispatch({ type: 'disconnected' })
        wsRef.current = null
        openRef.current = null
        // Free hosting sleeps when idle; keep retrying quietly so the UI recovers by itself.
        if (alive.current) setTimeout(() => { if (alive.current) reconnect.current() }, 3000)
      }
      ws.onmessage = async (e) => {
        if (stale()) return
        const msg = JSON.parse(e.data) as ServerMessage
        if (msg.type === 'hello') return setFeatures(msg.features)
        if (msg.type === 'exec_request') {
          const t0 = performance.now()
          const reply = await sandbox.run(msg.job, msg.timeout_s)
          const ok = (reply.result as { ok?: boolean } | undefined)?.ok
          dispatch({ type: 'exec', entry: {
            id: msg.id, kind: String(msg.job.kind), ms: Math.round(performance.now() - t0),
            outcome: reply.timed_out ? 'timeout' : ok ? 'ok' : 'error',
          } })
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'exec_result', id: msg.id, ...reply }))
          return
        }
        dispatch({ type: 'message', msg })
      }
    })
    openRef.current = opening
    opening.catch(() => { if (openRef.current === opening) openRef.current = null })
    return opening
  }, [])

  useEffect(() => {
    alive.current = true
    reconnect.current = () => { connect().catch(() => {}) }
    connect().catch(() => {})
    void sandbox.warmUp().catch(() => {})
    return () => {
      alive.current = false
      const ws = wsRef.current
      wsRef.current = null
      openRef.current = null
      ws?.close()
    }
  }, [connect])

  const solve = useCallback(async (problem: string, opts: SolveOptions) => {
    dispatch({ type: 'start', problem })
    try {
      const ws = await connect()
      ws.send(JSON.stringify({ type: 'solve', problem, solver: opts.solver, api_key: opts.apiKey, fresh: opts.fresh }))
    } catch (err) {
      dispatch({ type: 'fail', message: String((err as Error).message ?? err) })
    }
  }, [connect])

  const cancel = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ type: 'cancel' }))
    dispatch({ type: 'fail', message: 'Run cancelled.' })
  }, [])

  const reset = useCallback(() => dispatch({ type: 'reset' }), [])

  return { state, features, connected, solve, cancel, reset }
}
