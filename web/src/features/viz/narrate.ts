import type { Snap, TraceStep } from '../../lib/types'
import { isObj, same, show } from './snap'

/** Deterministic caption for a step: what the line is about to do and what just changed. */
export function narrate(step: TraceStep, prev: TraceStep | undefined, codeLines: string[]): string[] {
  if (step.event === 'call') {
    const args = Object.entries(step.locals).map(([k, v]) => `${k}=${show(v, 24)}`).join(', ')
    return [`Call ${step.func}(${args})`]
  }
  if (step.event === 'return') return [`${step.func} returns ${show(step.ret ?? null, 60)}`]

  const out: string[] = []
  if (prev && prev.func === step.func && prev.depth === step.depth) {
    for (const [name, value] of Object.entries(step.locals)) {
      const before = prev.locals[name]
      if (!(name in prev.locals)) out.push(`${name} = ${show(value, 32)}`)
      else if (!same(before, value)) out.push(describeChange(name, before, value))
    }
  } else if (prev && prev.depth > step.depth) {
    out.push(`back in ${step.func}`)
  }
  const code = codeLines[step.line - 1]?.trim()
  return [...out.slice(0, 4), ...(code ? [`next: ${code}`] : [])]
}

function describeChange(name: string, a: Snap, b: Snap): string {
  if (isObj(a) && isObj(b) && a.t === 'dict' && b.t === 'dict') {
    const before = new Map(a.entries.map(([k, v]) => [show(k), v]))
    const added = b.entries.filter(([k]) => !before.has(show(k)))
    const changed = b.entries.filter(([k, v]) => before.has(show(k)) && !same(before.get(show(k)), v))
    if (added.length === 1 && !changed.length) return `${name}[${show(added[0][0], 12)}] = ${show(added[0][1], 16)} (new)`
    if (changed.length === 1 && !added.length) return `${name}[${show(changed[0][0], 12)}]: ${show(before.get(show(changed[0][0]))!, 10)} → ${show(changed[0][1], 10)}`
    if (b.len < a.len) return `${name} removes ${a.len - b.len} entr${a.len - b.len === 1 ? 'y' : 'ies'}`
  }
  if (isObj(a) && isObj(b) && 'values' in a && 'values' in b && a.t !== 'tree' && b.t !== 'tree') {
    const av = a.values as Snap[], bv = b.values as Snap[]
    if (bv.length === av.length + 1 && same({ ...a, values: av } as Snap, { ...a, values: bv.slice(0, av.length) } as Snap)) {
      return `${name} gains ${show(bv[bv.length - 1], 16)}`
    }
    if (bv.length === av.length - 1) return `${name} drops an item (now ${bv.length})`
    if (bv.length === av.length) {
      const diffs = bv.map((v, i) => (same(v, av[i]) ? -1 : i)).filter((i) => i >= 0)
      if (diffs.length === 1) return `${name}[${diffs[0]}]: ${show(av[diffs[0]], 10)} → ${show(bv[diffs[0]], 10)}`
    }
  }
  return `${name}: ${show(a, 16)} → ${show(b, 16)}`
}
