import { describe, expect, it } from 'vitest'
import { lessonPath, parseLesson } from './route'
import { titleKey } from './roadmaps'

describe('lesson routes', () => {
  it('round-trips every lesson kind', () => {
    for (const r of [{ kind: 'roadmap', roadmap: 'blind75', ref: 'two-sum' }, { kind: 'library', id: 'coin-change' }, { kind: 'custom' }] as const) {
      expect(parseLesson(lessonPath(r))).toEqual(r)
    }
  })

  it('ignores other pages and unknown roadmaps', () => {
    expect(parseLesson('/')).toBeNull()
    expect(parseLesson('/roadmaps/blind75')).toBeNull()
    expect(parseLesson('/learn/other/two-sum')).toBeNull()
  })
})

describe('title matching', () => {
  it('treats spelled-out numbers and punctuation loosely', () => {
    expect(titleKey('Three Sum')).toBe(titleKey('3Sum'))
    expect(titleKey('LeetCode 1: Two Sum')).toBe(titleKey('Two Sum'))
  })
})
