import type { Snap, VizRole } from '../../lib/types'

export type Collection = Extract<Snap, { t: string; values: unknown }>

export function isObj(s: Snap): s is Exclude<Snap, null | boolean | number | string> {
  return typeof s === 'object' && s !== null
}

/** Short human-readable rendering of any snapshot. */
export function show(s: Snap, max = 40): string {
  let out: string
  if (s === null) out = 'None'
  else if (typeof s === 'boolean') out = s ? 'True' : 'False'
  else if (typeof s === 'string') out = JSON.stringify(s)
  else if (typeof s === 'number') out = Number.isInteger(s) ? String(s) : String(+s.toPrecision(6))
  else switch (s.t) {
    case 'list': case 'deque': out = `[${s.values.map((v) => show(v, 12)).join(', ')}${s.len > s.values.length ? ', …' : ''}]`; break
    case 'tuple': out = `(${s.values.map((v) => show(v, 12)).join(', ')})`; break
    case 'set': out = s.len ? `{${s.values.map((v) => show(v, 12)).join(', ')}}` : 'set()'; break
    case 'dict': out = `{${s.entries.map(([k, v]) => `${show(k, 10)}: ${show(v, 10)}`).join(', ')}}`; break
    case 'linked': out = s.values.map((v) => show(v, 8)).join(' → ') || 'None'; break
    case 'tree': out = `tree(${s.values.filter((v) => v !== null).length} nodes)`; break
    case 'obj': case 'num': out = s.repr; break
    default: out = '…'
  }
  return out.length > max ? out.slice(0, max - 1) + '…' : out
}

export function same(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b)
}

export function inferRole(s: Snap): VizRole {
  if (!isObj(s)) return 'scalar'
  switch (s.t) {
    case 'list': case 'tuple':
      return s.values.length > 0 && s.values.every((v) => isObj(v) && (v.t === 'list' || v.t === 'tuple')) ? 'grid' : 'array'
    case 'deque': return 'queue'
    case 'dict': return 'hashmap'
    case 'set': return 'set'
    case 'linked': return 'linked_list'
    case 'tree': return 'tree'
    default: return 'scalar'
  }
}

/** Is this a role the renderer can actually draw for this value? Guards against LLM mislabels. */
export function roleFits(role: VizRole, s: Snap): boolean {
  if (role === 'scalar' || role === 'pointer') return true
  if (!isObj(s)) return false
  const fits: Record<string, string[]> = {
    array: ['list', 'tuple', 'deque'], stack: ['list', 'deque'], queue: ['list', 'deque'],
    grid: ['list', 'tuple'], hashmap: ['dict'], set: ['set'], linked_list: ['linked'], tree: ['tree'],
  }
  return (fits[role] ?? []).includes(s.t)
}

const POINTER_NAMES = /^(i|j|k|l|r|lo|hi|mid|left|right|start|end|slow|fast|p|q|idx|index|ptr|cur|curr|head|tail|top|a|b)\d?$/

export function looksLikePointer(name: string): boolean {
  return POINTER_NAMES.test(name)
}
