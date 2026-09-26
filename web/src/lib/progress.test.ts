import { describe, expect, it } from 'vitest'
import { emptyProgress, mergeProgress, parseProgress, recordAttempt, REVIEW_INTERVALS_DAYS, statusOf } from './progress'

const DAY = 24 * 60 * 60 * 1000
const at = (d: number) => d * DAY

describe('spaced repetition', () => {
  it('a strong first lesson schedules a review in 3 days, then further out', () => {
    let p = recordAttempt(emptyProgress(), 'two-sum', { at: at(0), score: 1, mode: 'guided' })
    expect(p.items['two-sum'].nextDue).toBe(at(REVIEW_INTERVALS_DAYS[1]))
    expect(statusOf(p, 'two-sum', at(1))).toBe('learned')
    expect(statusOf(p, 'two-sum', at(4))).toBe('due')
    p = recordAttempt(p, 'two-sum', { at: at(4), score: 0.8, mode: 'guided' })
    expect(p.items['two-sum'].nextDue).toBe(at(4 + REVIEW_INTERVALS_DAYS[2]))
  })

  it('a weak lesson comes back tomorrow; reading along does not promote', () => {
    let p = recordAttempt(emptyProgress(), 'x', { at: at(0), score: 0.4, mode: 'guided' })
    expect(p.items.x.box).toBe(0)
    p = recordAttempt(p, 'x', { at: at(1), score: null, mode: 'walkthrough' })
    expect(p.items.x.box).toBe(0)
    expect(statusOf(p, 'unseen')).toBe('new')
  })

  it('imports merge by recency and reject garbage', () => {
    const a = recordAttempt(emptyProgress(), 'x', { at: at(1), score: 1, mode: 'guided' })
    const b = recordAttempt(emptyProgress(), 'x', { at: at(5), score: 0.2, mode: 'guided' })
    expect(mergeProgress(a, b).items.x.lastAt).toBe(at(5))
    expect(parseProgress('{"nope":1}')).toBeNull()
    expect(parseProgress(JSON.stringify(a))).toEqual(a)
  })
})
