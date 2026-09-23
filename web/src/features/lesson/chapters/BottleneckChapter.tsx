import { Check, Lightbulb } from 'lucide-react'
import { useState } from 'react'
import { Button } from '../../../components/ui'
import { CodeView, type LineMark } from '../../viz/CodeView'
import { useLesson } from '../context'
import { SizePicker, useLineHeat } from '../lineHeat'
import { Callout, ContinueBar, Prose } from '../parts'

export function BottleneckChapter() {
  const { state, guided, record } = useLesson()
  const intro = state.lessonIntro!
  const target = intro.bottleneck_line
  const [wrong, setWrong] = useState<number[]>([])
  const [hints, setHints] = useState(0)
  const [solved, setSolved] = useState(false)
  const [revealed, setRevealed] = useState(false)
  const [n, setN] = useState<number | null>(null)
  const open = !guided || solved || revealed || target === null
  const brute = state.lineCounts?.brute_force
  const { run, heat, gutter } = useLineHeat(brute, n)

  const click = (line: number) => {
    if (open) return
    if (line === target) {
      setSolved(true)
      record('bottleneck', { correct: wrong.length === 0 ? 1 : 0, total: 1 })
    } else if (!wrong.includes(line)) {
      setWrong([...wrong, line])
      setHints((h) => Math.min(intro.bottleneck_hints.length, h + 1))
    }
  }
  const marks: Record<number, LineMark> = {}
  wrong.forEach((l) => { marks[l] = 'wrong' })
  if (open && target) marks[target] = 'correct'

  return (
    <div>
      {!open && <Prose className="mb-3 font-medium">Click the line that does the most repeated, wasted work as the input grows.</Prose>}
      {intro.brute_is_optimal && <Prose className="mb-3 font-medium">There's no wasted work to find here. Here's why the direct approach can't be beaten.</Prose>}
      <CodeView
        code={intro.brute_force_code} maxHeight={360} marks={marks}
        onLineClick={open ? undefined : click}
        heat={open ? heat : undefined} gutter={open ? gutter : undefined}
      />
      {!open && (
        <div className="mt-3 grid gap-2">
          {intro.bottleneck_hints.slice(0, hints).map((h, k) => (
            <Callout key={k} tone="warn" icon={<Lightbulb className="size-4" />}><span className="font-medium">Hint {k + 1}. </span>{h}</Callout>
          ))}
          <div className="flex items-center gap-3 text-xs text-faint">
            {hints < intro.bottleneck_hints.length && <Button variant="ghost" className="text-xs" onClick={() => setHints(hints + 1)}>Give me a hint</Button>}
            <button onClick={() => setRevealed(true)} className="underline-offset-2 hover:text-muted hover:underline">Show me the answer</button>
          </div>
        </div>
      )}
      {open && (
        <div className="mt-4 grid gap-3">
          {guided && solved && <p className="flex items-center gap-1.5 text-[13.5px] font-medium text-ok"><Check className="size-4" strokeWidth={2.5} />{wrong.length ? 'Found it.' : 'Found it on the first try.'}</p>}
          <Prose>{intro.bottleneck}</Prose>
          {brute && run ? (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-sunken px-3.5 py-2.5">
              <span className="text-[12.5px] text-muted">
                The shading shows how many times each line actually ran on a {state.lineCounts?.used_worst_case ? 'worst-case' : 'random'} input of size n. Switch sizes and watch the hot line grow.
              </span>
              <SizePicker runs={brute} n={run.n} setN={setN} />
            </div>
          ) : state.status === 'running' && <p className="text-xs text-faint">Counting how often each line runs…</p>}
        </div>
      )}
      <ContinueBar id="bottleneck" enabled={open} />
    </div>
  )
}
