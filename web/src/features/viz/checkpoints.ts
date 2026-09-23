import type { TraceStep } from '../../lib/types'

/** A moment in the trace where a guided learner is asked to predict what happens next. */
export type Checkpoint =
  | { kind: 'branch'; step: number; condition: string; keyword: 'if' | 'elif' | 'while'; answer: boolean }
  | { kind: 'return'; step: number }

const indent = (s: string | undefined) => (s ? s.length - s.trimStart().length : 0)

/**
 * Derive prediction questions from a real execution trace. Branch outcomes are read off the
 * trace itself (did execution enter the indented block next?), so answers are always exact.
 */
export function findCheckpoints(steps: TraceStep[], code: string, max = 3): Checkpoint[] {
  const lines = code.split('\n')
  const branches: Extract<Checkpoint, { kind: 'branch' }>[] = []
  steps.forEach((s, i) => {
    if (s.event !== 'line') return
    const text = lines[s.line - 1]?.trim() ?? ''
    const m = text.match(/^(if|elif|while)\s+(.+):\s*$/) // skip one-liners like `if x: return y`
    if (!m) return
    const next = steps.slice(i + 1).find((t) => t.depth === s.depth && t.func === s.func && t.event !== 'call')
    if (!next || next.event !== 'line') return
    const entered = next.line > s.line && indent(lines[next.line - 1]) > indent(lines[s.line - 1])
    branches.push({ kind: 'branch', step: i, keyword: m[1] as 'if' | 'elif' | 'while', condition: m[2], answer: entered })
  })

  // Mix outcomes: the first True, the first False, then one from later in the run.
  const picked = new Map<number, Checkpoint>()
  const firstTrue = branches.find((b) => b.answer)
  const firstFalse = branches.find((b) => !b.answer)
  for (const b of [firstFalse, firstTrue]) if (b) picked.set(b.step, b)
  const late = branches.filter((b) => b.step > steps.length * 0.55 && !picked.has(b.step))
  if (late.length && picked.size < max) picked.set(late[0].step, late[0])

  const out = [...picked.values()].slice(0, max)
  const finalReturn = steps.findLastIndex((s) => s.event === 'return' && s.depth === 1)
  if (finalReturn > 0) out.push({ kind: 'return', step: finalReturn })
  return out.sort((a, b) => a.step - b.step)
}
