import clsx from 'clsx'
import { type ReactNode, useEffect, useRef } from 'react'

const KEYWORDS = new Set('and as assert break class continue def del elif else except False finally for from global if import in is lambda None nonlocal not or pass raise return True try while with yield'.split(' '))
const BUILTINS = new Set('len range enumerate min max sum sorted abs zip map list dict set tuple int str float bool any all reversed print heappush heappop defaultdict deque Counter inf self'.split(' '))
const TOKEN = /(#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|(.)/g

function highlight(line: string) {
  const parts: { text: string; cls?: string }[] = []
  let prevWord = ''
  for (const m of line.matchAll(TOKEN)) {
    const [text, comment, str, num, word] = m
    let cls: string | undefined
    if (comment) cls = 'text-faint italic'
    else if (str) cls = 'text-ok'
    else if (num) cls = 'text-viz-3'
    else if (word && KEYWORDS.has(word)) cls = 'text-viz-4'
    else if (word && (prevWord === 'def' || prevWord === 'class')) cls = 'text-viz-1 font-semibold'
    else if (word && BUILTINS.has(word)) cls = 'text-viz-2'
    if (word) prevWord = word
    parts.push({ text, cls })
  }
  return parts
}

export type LineMark = 'correct' | 'wrong' | 'focus'

interface Props {
  code: string
  /** Current execution line (visualizer). */
  line?: number
  prevLine?: number
  event?: string
  /** Make lines clickable (e.g. "click the bottleneck"). */
  onLineClick?: (line: number) => void
  marks?: Record<number, LineMark>
  /** 0..1 intensity per line, drawn as a heat bar (e.g. how often the line ran). */
  heat?: Record<number, number>
  /** Content shown at the right edge of a line (counts, cost badges). */
  gutter?: Record<number, ReactNode>
  maxHeight?: number
}

export function CodeView({ code, line, prevLine, event, onLineClick, marks, heat, gutter, maxHeight = 520 }: Props) {
  const lines = code.replace(/\s+$/, '').split('\n')
  const box = useRef<HTMLDivElement>(null)
  const active = useRef<HTMLDivElement>(null)
  useEffect(() => {
    // Scroll only the code box (scrollIntoView would also scroll the page while playing).
    const b = box.current, a = active.current
    if (!b || !a) return
    if (a.offsetTop < b.scrollTop || a.offsetTop + a.offsetHeight > b.scrollTop + b.clientHeight) {
      b.scrollTo({ top: a.offsetTop - b.clientHeight / 3, behavior: 'smooth' })
    }
  }, [line])
  return (
    <div ref={box} className="relative overflow-auto rounded-lg bg-sunken py-2 font-mono text-[12.5px] leading-[1.75]" style={{ maxHeight }}>
      {lines.map((l, i) => {
        const n = i + 1
        const isActive = n === line
        const mark = marks?.[n]
        const h = heat?.[n] ?? 0
        const Row = onLineClick ? 'button' : 'div'
        return (
          <Row
            key={i} ref={isActive ? (active as never) : undefined}
            onClick={onLineClick ? () => onLineClick(n) : undefined}
            className={clsx('relative flex w-full whitespace-pre pr-3 text-left',
              onLineClick && 'cursor-pointer hover:bg-accent/10',
              isActive && (event === 'return' ? 'bg-ok-soft' : 'bg-accent-soft'),
              !isActive && n === prevLine && 'bg-line/40',
              mark === 'correct' && 'bg-ok-soft', mark === 'wrong' && 'bg-bad-soft', mark === 'focus' && 'bg-warn-soft')}
          >
            {h > 0 && <span className="absolute inset-y-0.5 left-10 rounded-sm bg-viz-3/20" style={{ width: `calc(${Math.max(4, h * 100)}% - 2.5rem)` }} />}
            {(isActive || mark) && (
              <span className={clsx('absolute inset-y-0 left-0 w-[3px]',
                mark === 'correct' || (isActive && event === 'return') ? 'bg-ok' : mark === 'wrong' ? 'bg-bad' : mark === 'focus' ? 'bg-warn' : 'bg-accent')} />
            )}
            <span className={clsx('relative w-10 shrink-0 select-none pr-3 text-right', isActive ? 'text-accent' : 'text-faint')}>{n}</span>
            <span className="relative flex-1">{highlight(l).map((p, j) => <span key={j} className={p.cls}>{p.text}</span>)}</span>
            {gutter?.[n] !== undefined && <span className="relative ml-3 shrink-0 font-sans">{gutter[n]}</span>}
          </Row>
        )
      })}
    </div>
  )
}
