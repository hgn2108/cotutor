import { describe, expect, it } from 'vitest'
import type { TraceStep } from '../../lib/types'
import { findCheckpoints } from './checkpoints'

const code = [
  'def f(nums):',          // 1
  '    total = 0',         // 2
  '    for x in nums:',    // 3
  '        if x > 0:',     // 4
  '            total += x',// 5
  '    return total',      // 6
].join('\n')

const step = (line: number, event: TraceStep['event'] = 'line'): TraceStep =>
  ({ event, line, func: 'f', depth: 1, locals: {} })

describe('findCheckpoints', () => {
  it('reads branch outcomes off the trace itself', () => {
    // nums = [-1, 2]: first `if` is false (skips to loop), second is true (enters body)
    const steps = [step(1, 'call'), step(2), step(3), step(4), step(3), step(4), step(5), step(3), step(6), step(6, 'return')]
    const cps = findCheckpoints(steps, code)
    const branches = cps.filter((c) => c.kind === 'branch')
    expect(branches.map((b) => b.kind === 'branch' && b.answer)).toEqual([false, true])
    expect(cps.at(-1)).toEqual({ kind: 'return', step: 9 })
  })
})
