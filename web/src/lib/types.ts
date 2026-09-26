// Mirrors backend/cotutor/schemas.py and the events emitted by pipeline.py.

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json }

export interface Param { name: string; type: string }
export interface ProblemSpec {
  is_solvable: boolean
  title: string
  kind: 'function' | 'design'
  summary: string
  entry: string
  params: Param[]
  return_type: string
  examples: { args_json: string; expected_json: string }[]
  constraints: string[]
  comparison: 'exact' | 'unordered' | 'unordered_nested' | 'float'
  multiple_valid_answers: boolean
  in_place_arg: number
  pattern_tags: string[]
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface TestPlan {
  cases: { name: string; category: string; args_json: string; rationale: string }[]
  reference_solution: string
  generator_code: string
  checker_code: string
}

export interface Solution {
  approach: string
  key_insight: string
  steps: { title: string; detail: string }[]
  code: string
  time_complexity: string
  space_complexity: string
  revision: number
}

export interface HarnessError { type: string; message: string; where: string[] }

export interface CaseDef {
  id: string
  args: Json[]
  expected?: Json
  source: 'example' | 'reference' | 'stress'
  label: string
  category?: string
  rationale?: string
}

export interface CaseResult {
  id: string
  status: 'pass' | 'fail' | 'error' | 'timeout' | 'ran' | 'skipped'
  expected?: Json
  expected_source?: string
  got?: Json
  stdout?: string
  error?: HarnessError
  ms?: number
}

export interface Verification {
  attempt: number
  verified: boolean
  results: CaseResult[]
  cases: CaseDef[]
  stress_trials: number
  counterexample: { args: Json[]; expected: Json; got?: Json; error?: HarnessError } | null
  load_error: HarnessError | null
}

export interface DebugAttempt {
  attempt: number
  diagnosis: string
  fix_summary: string
  before: string
  after: string
}

export interface Complexity {
  points: [number, number][]
  slope: number | null
  claimed: string
  expected_slope: number | null
  verdict: 'consistent' | 'slower_than_claimed' | 'faster_than_claimed' | 'inconclusive'
  note: string
  used_worst_case: boolean
}

export interface FlowNode { id: string; label: string; kind: 'start' | 'step' | 'decision' | 'loop' | 'end'; detail: string }
export interface FlowEdge { source: string; target: string; label: string }
export type VizRole =
  | 'array' | 'pointer' | 'hashmap' | 'set' | 'grid' | 'stack' | 'queue' | 'linked_list' | 'tree' | 'scalar'
export interface Explanation {
  overview: string
  intuition: string
  flow_nodes: FlowNode[]
  flow_edges: FlowEdge[]
  pitfalls: string[]
  viz_vars: { name: string; role: VizRole; target: string }[]
  viz_args_json: string
  similar_problems: string[]
}

// Typed runtime snapshots produced by harness.snapshot()
export type Snap =
  | null | boolean | number | string
  | { t: 'list' | 'tuple' | 'deque' | 'set'; values: Snap[]; len: number }
  | { t: 'dict'; entries: [Snap, Snap][]; len: number }
  | { t: 'linked'; values: Snap[]; id: number }
  | { t: 'tree'; values: (number | string | null)[]; id: number }
  | { t: 'obj' | 'num'; repr: string }
  | { t: 'more' }

export interface TraceStep {
  event: 'line' | 'call' | 'return'
  line: number
  func: string
  depth: number
  locals: Record<string, Snap>
  ret?: Snap
}

export interface Trace {
  steps: TraceStep[]
  truncated: boolean
  result: Json
  error: HarnessError | null
  args: Json[]
  code: string
}

export interface StageEvent {
  type: 'stage'
  id: string
  label: string
  status: 'running' | 'done' | 'failed' | 'warning' | 'skipped'
  detail?: string
  ms?: number
  tokens?: number
  models?: string[]
}

export interface Summary {
  verified: boolean
  attempts?: number
  tests_passed?: number
  tests_total?: number
  stress_trials?: number
  complexity_verdict?: Complexity['verdict'] | null
  input_tokens: number
  output_tokens: number
  llm_calls: number
  ms: number
  replayed?: boolean
  recording?: 'live' | 'scripted' | 'cache'
  error?: string
}

export interface LibraryProblem {
  id: string
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
  statement: string
}

export type ServerMessage =
  | { type: 'hello'; features: Features }
  | { type: 'problem'; text: string; by_name: boolean }
  | StageEvent
  | { type: 'artifact'; name: string; data: unknown }
  | { type: 'exec_request'; id: string; job: Record<string, unknown>; timeout_s: number }
  | { type: 'error'; message: string; code?: string }
  | { type: 'done'; summary: Summary }

export interface Features {
  server_key: boolean
  models: { smart: string; fast: string }
}

// Coach lesson (backend schemas.LessonIntro / LessonDeep, plus fields the pipeline adds)
export interface LessonIntro {
  pattern: string
  pattern_summary: string
  pattern_options: { name: string; correct: boolean; feedback: string }[]
  signals: { phrase: string; hint: string }[]
  brute_force_idea: string
  brute_force_time: string
  brute_force_why: string
  bottleneck_line: number | null
  bottleneck: string
  bottleneck_hints: string[]
  brute_force_code: string
  brute_is_optimal?: boolean
}

export interface LessonDeep {
  insight: string
  derivation: { line: number; cost: string; note: string }[]
  time_summary: string
  space_summary: string
  takeaway: string
  mistakes: string[]
  code: string
}

export interface LineCountRun { n: number; total: number; capped: boolean; counts: Record<string, number> }
export interface LineCounts { solution: LineCountRun[]; brute_force?: LineCountRun[]; used_worst_case: boolean }
