import { describe, expect, it } from 'vitest'
import { answersMatch, normalizeBigO, parseAnswer, seededShuffle } from './answers'

describe('parseAnswer', () => {
  it('accepts JSON and Python-style literals', () => {
    expect(parseAnswer('[1, 2]')).toEqual({ ok: true, value: [1, 2] })
    expect(parseAnswer('True')).toEqual({ ok: true, value: true })
    expect(parseAnswer('None')).toEqual({ ok: true, value: null })
    expect(parseAnswer("['a', 'b']")).toEqual({ ok: true, value: ['a', 'b'] })
    expect(parseAnswer('(1, 2)')).toEqual({ ok: true, value: [1, 2] })
  })
  it('rejects empty input', () => {
    expect(parseAnswer('   ').ok).toBe(false)
  })
})

describe('answersMatch', () => {
  it('respects the comparison mode', () => {
    expect(answersMatch([1, 0], [0, 1], 'exact')).toBe(false)
    expect(answersMatch([1, 0], [0, 1], 'unordered')).toBe(true)
    expect(answersMatch([[2, 1], [3]], [[3], [1, 2]], 'unordered_nested')).toBe(true)
    expect(answersMatch(0.30000000000000004, 0.3, 'float')).toBe(true)
  })
})

describe('normalizeBigO', () => {
  it('maps common spellings to canonical options', () => {
    expect(normalizeBigO('O(n^2)')).toBe('O(n²)')
    expect(normalizeBigO('O(N log N)')).toBe('O(n log n)')
    expect(normalizeBigO('O(n * m)')).toBeNull()
  })
})

describe('seededShuffle', () => {
  it('is deterministic and keeps every item', () => {
    const items = ['a', 'b', 'c', 'd']
    expect(seededShuffle(items, 'x')).toEqual(seededShuffle(items, 'x'))
    expect([...seededShuffle(items, 'x')].sort()).toEqual(items)
  })
})
