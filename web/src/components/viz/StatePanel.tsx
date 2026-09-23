import type { Explanation, Snap, TraceStep, VizRole } from '../../lib/types'
import { ArrayView, GridView, LinkedView, MapView, type Pointer, ScalarsView, SetView, StackView, TreeView } from './renderers'
import { inferRole, isObj, looksLikePointer, roleFits, show } from './snap'

/** For each step, the call stack (function names) at that point, rebuilt from call/return events. */
export function callStacks(steps: TraceStep[]): string[][] {
  const stacks: string[][] = []
  let stack: string[] = []
  for (const s of steps) {
    if (s.event === 'call') stack = [...stack, s.func]
    stacks.push(stack)
    if (s.event === 'return') stack = stack.slice(0, -1)
  }
  return stacks
}

interface Plan { name: string; role: VizRole; target?: string }

/** Decide how to draw each variable: the tutor's hints first, then type-based inference. */
function planVariables(step: TraceStep, explanation?: Explanation): Plan[] {
  const hints = new Map(explanation?.viz_vars.map((v) => [v.name, v]) ?? [])
  const plans: Plan[] = []
  for (const [name, value] of Object.entries(step.locals)) {
    const hint = hints.get(name)
    let role: VizRole = hint && roleFits(hint.role, value) ? hint.role : inferRole(value)
    if (role === 'pointer' && typeof value !== 'number') role = inferRole(value)
    plans.push({ name, role, target: hint?.target || undefined })
  }
  const rank = (p: Plan) => {
    const i = explanation?.viz_vars.findIndex((v) => v.name === p.name) ?? -1
    return i < 0 ? 100 : i
  }
  return plans.sort((a, b) => rank(a) - rank(b))
}

function pointersFor(arrayName: string, arr: Snap, step: TraceStep, plans: Plan[], firstArray: string | undefined): Pointer[] {
  if (!isObj(arr) || !('values' in arr)) return []
  const len = (arr as { len: number }).len
  const out: Pointer[] = []
  for (const p of plans) {
    const v = step.locals[p.name]
    if (typeof v !== 'number' || !Number.isInteger(v) || v < 0 || v > len) continue
    const explicit = p.role === 'pointer' && (p.target ? p.target === arrayName : arrayName === firstArray)
    const inferred = p.role === 'scalar' && !p.target && looksLikePointer(p.name) && arrayName === firstArray && v < len
    if (explicit || inferred) out.push({ name: p.name, index: v })
  }
  return out
}

function gridCursor(step: TraceStep): [number, number] | undefined {
  for (const [a, b] of [['i', 'j'], ['r', 'c'], ['row', 'col'], ['x', 'y']]) {
    const i = step.locals[a], j = step.locals[b]
    if (typeof i === 'number' && typeof j === 'number') return [i, j]
  }
  return undefined
}

export function StatePanel({ step, prev, explanation, hideReturn }: { step: TraceStep; prev?: TraceStep; explanation?: Explanation; hideReturn?: boolean }) {
  const plans = planVariables(step, explanation)
  const prevLocals = prev && prev.func === step.func && prev.depth === step.depth ? prev.locals : undefined
  const firstArray = plans.find((p) => p.role === 'array')?.name
  const drawnAsPointer = new Set<string>()
  const structures = plans.filter((p) => !['scalar', 'pointer'].includes(p.role))
  const blocks = structures.map((p) => {
    const snap = step.locals[p.name]
    const before = prevLocals?.[p.name]
    if (!isObj(snap)) return null
    switch (p.role) {
      case 'array': {
        const ptrs = pointersFor(p.name, snap, step, plans, firstArray)
        ptrs.forEach((x) => drawnAsPointer.add(x.name))
        return <ArrayView key={p.name} name={p.name} snap={snap as never} prev={before} pointers={ptrs} />
      }
      case 'stack': return <StackView key={p.name} name={p.name} snap={snap as never} prev={before} />
      case 'queue': return <StackView key={p.name} name={p.name} snap={snap as never} prev={before} horizontal />
      case 'hashmap': return <MapView key={p.name} name={p.name} snap={snap as never} prev={before} />
      case 'set': return <SetView key={p.name} name={p.name} snap={snap as never} prev={before} />
      case 'grid': return <GridView key={p.name} name={p.name} snap={snap as never} prev={before} cursor={gridCursor(step)} />
      case 'linked_list': return <LinkedView key={p.name} name={p.name} snap={snap as never} prev={before} />
      case 'tree': return <TreeView key={p.name} name={p.name} snap={snap as never} prev={before} />
      default: return null
    }
  })
  const scalars = plans
    .filter((p) => p.role === 'scalar' || p.role === 'pointer')
    .map((p) => ({ name: p.name, value: step.locals[p.name], changed: !!prevLocals && JSON.stringify(prevLocals[p.name]) !== JSON.stringify(step.locals[p.name]) }))
  return (
    <div className="grid gap-5">
      {scalars.length > 0 && <ScalarsView items={scalars.sort((a, b) => Number(drawnAsPointer.has(b.name)) - Number(drawnAsPointer.has(a.name)))} />}
      {blocks}
      {step.event === 'return' && !hideReturn && (
        <div className="rounded-lg border border-ok/40 bg-ok-soft px-3 py-2 font-mono text-[13px] text-ok">return {show(step.ret ?? null, 80)}</div>
      )}
      {!blocks.some(Boolean) && !scalars.length && <div className="text-sm text-faint">No local variables yet.</div>}
    </div>
  )
}

