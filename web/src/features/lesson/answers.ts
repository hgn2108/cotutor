import type { Json, ProblemSpec } from '../../lib/types'

/** Parse what a learner typed. Accepts JSON and Python-style literals (True, None, 'x', tuples). */
export function parseAnswer(raw: string): { ok: true; value: Json } | { ok: false } {
  const text = raw.trim()
  if (!text) return { ok: false }
  const pythonish = text
    .replace(/\bTrue\b/g, 'true').replace(/\bFalse\b/g, 'false').replace(/\bNone\b/g, 'null')
    .replace(/'([^'\\]*)'/g, '"$1"')
    .replace(/\(/g, '[').replace(/\)/g, ']')
    .replace(/,\s*([\]}])/g, '$1')
  for (const candidate of [text, pythonish]) {
    try {
      return { ok: true, value: JSON.parse(candidate) as Json }
    } catch { /* try next */ }
  }
  return { ok: true, value: text.replace(/^"|"$/g, '') } // bare word, e.g. abc for a string answer
}

const canon = (v: unknown) => JSON.stringify(v)

export function answersMatch(got: Json, expected: Json, comparison: ProblemSpec['comparison']): boolean {
  if (comparison === 'float' && typeof got === 'number' && typeof expected === 'number') {
    return Math.abs(got - expected) <= 1e-6 * Math.max(1, Math.abs(expected))
  }
  if ((comparison === 'unordered' || comparison === 'unordered_nested') && Array.isArray(got) && Array.isArray(expected)) {
    const norm = (xs: Json[]) => xs.map((x) => (comparison === 'unordered_nested' && Array.isArray(x) ? canon([...x].map(canon).sort()) : canon(x))).sort()
    return canon(norm(got)) === canon(norm(expected))
  }
  return canon(got) === canon(expected)
}

/** Deterministic shuffle so options don't jump around between renders. */
export function seededShuffle<T>(items: T[], seed: string): T[] {
  let h = 2166136261
  for (const c of seed) h = Math.imul(h ^ c.charCodeAt(0), 16777619)
  const out = [...items]
  for (let i = out.length - 1; i > 0; i--) {
    h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0
    const j = h % (i + 1)
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

const BIG_O = ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(2ⁿ)']

/** Normalize a Big-O string to one of BIG_O, or null if it's something more specific. */
export function normalizeBigO(s: string): string | null {
  const t = s.toLowerCase().replace(/\s+/g, '').replace(/\*/g, '').replace(/\^2|²/g, '²').replace(/\^n|ⁿ/g, 'ⁿ')
  const table: Record<string, string> = {
    'o(1)': 'O(1)', 'o(logn)': 'O(log n)', 'o(n)': 'O(n)', 'o(nlogn)': 'O(n log n)',
    'o(n²)': 'O(n²)', 'o(2ⁿ)': 'O(2ⁿ)',
  }
  return table[t] ?? null
}

export const bigOOptions = BIG_O
