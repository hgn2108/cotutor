import clsx from 'clsx'
import { Check, ChevronFirst, ChevronLast, ChevronLeft, ChevronRight, HelpCircle, Pause, Play, X } from 'lucide-react'
import { type ReactNode, useEffect, useMemo, useState } from 'react'
import type { Explanation, Trace, TraceStep } from '../../lib/types'
import { answersMatch, parseAnswer } from '../lesson/answers'
import { Badge, Button, Card, formatJson, Mono } from '../ui'
import { type Checkpoint, findCheckpoints } from './checkpoints'
import { CodeView } from './CodeView'
import { narrate } from './narrate'
import { show } from './snap'
import { callStacks, StatePanel } from './StatePanel'

const SPEEDS = [0.5, 1, 2, 4]

interface Props {
  trace: Trace
  explanation?: Explanation
  /** Guided mode pauses at checkpoints and asks the learner to predict what happens next. */
  guided?: boolean
  onProgress?: (p: { reachedEnd: boolean; answered: number; correct: number; total: number }) => void
}

type Answer = { correct: boolean | null } // null = revealed without answering

export function Player({ trace, explanation, guided = false, onProgress }: Props) {
  const steps = trace.steps
  const [i, setI] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [answers, setAnswers] = useState<Record<number, Answer>>({})
  const [reachedEnd, setReachedEnd] = useState(false)
  const stacks = useMemo(() => callStacks(steps), [steps])
  const codeLines = useMemo(() => trace.code.split('\n'), [trace.code])
  const checkpoints = useMemo(() => (guided ? findCheckpoints(steps, trace.code) : []), [guided, steps, trace.code])
  const last = steps.length - 1
  const checkpoint = checkpoints.find((c) => c.step === i)
  const blocked = !!checkpoint && !answers[checkpoint.step]

  const go = (next: number) => {
    const target = Math.max(0, Math.min(last, next))
    // In guided mode, stepping forward stops at the next unanswered checkpoint.
    const gate = guided ? checkpoints.find((c) => c.step > i && c.step < target && !answers[c.step]) : undefined
    const to = gate ? gate.step : target
    setI(to)
    if (to === last) setReachedEnd(true)
  }

  useEffect(() => {
    if (!playing) return
    // Stop at the end, or at a checkpoint that still needs an answer.
    const t = setTimeout(() => (i >= last || blocked ? setPlaying(false) : go(i + 1)), blocked ? 0 : 700 / speed)
    return () => clearTimeout(t)
  }, [playing, i, last, blocked, speed]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const vals = Object.values(answers)
    onProgress?.({ reachedEnd, answered: vals.length, correct: vals.filter((a) => a.correct).length, total: checkpoints.length })
  }, [answers, reachedEnd, checkpoints.length, onProgress])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).closest('input, textarea, .monaco-editor')) return
      if (e.key === 'ArrowRight') { setPlaying(false); if (!blocked) go(i + 1) }
      else if (e.key === 'ArrowLeft') { setPlaying(false); go(i - 1) }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  if (!steps.length) return <Card className="p-5 text-sm text-muted">The trace is empty. {trace.error && `${trace.error.type}: ${trace.error.message}`}</Card>
  const step = steps[i]
  const prev = i > 0 ? steps[i - 1] : undefined
  const caption = narrate(step, prev, codeLines)
  const stack = stacks[i]

  return (
    <div className="grid gap-4">
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1">
            <IconBtn label="First step" onClick={() => { setPlaying(false); setI(0) }}><ChevronFirst className="size-4" /></IconBtn>
            <IconBtn label="Previous step" onClick={() => { setPlaying(false); go(i - 1) }}><ChevronLeft className="size-4" /></IconBtn>
            <button
              onClick={() => { if (i >= last) setI(0); setPlaying((p) => !p) }} disabled={blocked} aria-label={playing ? 'Pause' : 'Play'}
              className="flex size-9 items-center justify-center rounded-full bg-accent text-white shadow-sm hover:brightness-110 disabled:opacity-40 dark:text-[#0e0e13]"
            >
              {playing ? <Pause className="size-4" /> : <Play className="ml-0.5 size-4" />}
            </button>
            <IconBtn label="Next step" disabled={blocked} onClick={() => { setPlaying(false); go(i + 1) }}><ChevronRight className="size-4" /></IconBtn>
            <IconBtn label="Last step" disabled={guided} onClick={() => { setPlaying(false); go(last) }}><ChevronLast className="size-4" /></IconBtn>
          </div>
          <div className="relative min-w-[140px] flex-1">
            <input
              type="range" min={0} max={last} value={i} aria-label="Step"
              onChange={(e) => { setPlaying(false); go(+e.target.value) }}
              className="w-full accent-[var(--color-accent)]"
            />
            {checkpoints.map((c) => (
              <span key={c.step} title="Prediction checkpoint"
                className={clsx('pointer-events-none absolute -top-1.5 size-2 -translate-x-1/2 rounded-full',
                  answers[c.step]?.correct ? 'bg-ok' : answers[c.step] ? 'bg-warn' : 'bg-viz-3')}
                style={{ left: `${(c.step / Math.max(1, last)) * 100}%` }} />
            ))}
          </div>
          <span className="font-mono text-xs tabular-nums text-muted">{i + 1} / {steps.length}</span>
          <div className="flex rounded-lg bg-sunken p-0.5 text-[11px]">
            {SPEEDS.map((s) => (
              <button key={s} onClick={() => setSpeed(s)} className={clsx('rounded-md px-1.5 py-0.5 font-mono', speed === s ? 'bg-panel shadow-sm' : 'text-muted')}>{s}×</button>
            ))}
          </div>
        </div>
        {checkpoint ? (
          <CheckpointCard
            key={checkpoint.step} checkpoint={checkpoint} step={step} trace={trace} answer={answers[checkpoint.step]}
            onAnswer={(a) => setAnswers((prevA) => ({ ...prevA, [checkpoint.step]: a }))}
            onContinue={() => { go(i + 1); setPlaying(true) }}
          />
        ) : (
          <div className="mt-3 flex min-h-[44px] flex-wrap items-start gap-x-4 gap-y-1 rounded-lg bg-sunken px-3 py-2 text-[13px]">
            {caption.map((c, k) => (
              <span key={k} className={clsx(c.startsWith('next:') ? 'font-mono text-[12px] text-muted' : 'font-medium')}>{c}</span>
            ))}
          </div>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <Card className="p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Code</span>
            {stack.length > 1 && <Badge tone="accent">recursion depth {stack.length}</Badge>}
          </div>
          <CodeView code={trace.code} line={step.line} prevLine={prev?.line} event={step.event} />
          <div className="mt-3 text-[12px] text-muted">
            Input <Mono>{formatJson(trace.args, 120)}</Mono>
            {(!guided || reachedEnd) && trace.result !== null && <> · returns <Mono>{formatJson(trace.result, 60)}</Mono></>}
          </div>
          {trace.truncated && <p className="mt-1 text-[11.5px] text-warn">Trace truncated at {steps.length} steps.</p>}
        </Card>
        <Card className="p-4">
          <div className="mb-3 flex flex-wrap items-center gap-1.5">
            <span className="mr-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">State</span>
            {stack.map((f, k) => (
              <span key={k} className={clsx('rounded px-1.5 py-0.5 font-mono text-[11px]', k === stack.length - 1 ? 'bg-accent-soft text-accent' : 'bg-sunken text-faint')}>{f}()</span>
            ))}
          </div>
          <StatePanel step={step} prev={prev} explanation={explanation} hideReturn={blocked} />
        </Card>
      </div>
      <p className="text-center text-[11.5px] text-faint">
        ← → to step{guided && checkpoints.length > 0 && <> · <span className="text-viz-3">●</span> marks a prediction checkpoint</>} · every frame comes from actually running the verified code
      </p>
    </div>
  )
}

function CheckpointCard({ checkpoint, step, trace, answer, onAnswer, onContinue }: {
  checkpoint: Checkpoint; step: TraceStep; trace: Trace; answer?: Answer
  onAnswer: (a: Answer) => void; onContinue: () => void
}) {
  const [guess, setGuess] = useState('')
  if (checkpoint.kind === 'branch') {
    const names = Object.keys(step.locals).filter((n) => new RegExp(`\\b${n}\\b`).test(checkpoint.condition))
    const context = names.map((n) => `${n} = ${show(step.locals[n], 28)}`).join(', ')
    const question = checkpoint.keyword === 'while' ? 'Will the loop body run again?' : 'Will this condition be true?'
    return (
      <div className="mt-3 rounded-lg border border-viz-3/40 bg-warn-soft/40 p-3.5">
        <div className="flex items-start gap-2">
          <HelpCircle className="mt-0.5 size-4 shrink-0 text-warn" />
          <div className="min-w-0 flex-1">
            <div className="text-[13.5px] font-medium">Predict: {question}</div>
            <div className="mt-1 font-mono text-[12.5px]">{checkpoint.keyword} {checkpoint.condition}</div>
            {context && <div className="mt-1 text-[12px] text-muted">Right now: <span className="font-mono">{context}</span></div>}
            {!answer ? (
              <div className="mt-2.5 flex flex-wrap gap-2">
                <Button variant="outline" onClick={() => onAnswer({ correct: checkpoint.answer === true })}>Yes, true</Button>
                <Button variant="outline" onClick={() => onAnswer({ correct: checkpoint.answer === false })}>No, false</Button>
                <Button variant="ghost" className="text-xs" onClick={() => onAnswer({ correct: null })}>Just show me</Button>
              </div>
            ) : (
              <div className="mt-2.5 flex flex-wrap items-center gap-3">
                <Verdict correct={answer.correct}>
                  It's <b>{checkpoint.answer ? 'true' : 'false'}</b>{checkpoint.answer ? ', so execution enters the block.' : ', so execution skips the block.'}
                </Verdict>
                <Button onClick={onContinue} className="py-1.5">Continue <ChevronRight className="size-3.5" /></Button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="mt-3 rounded-lg border border-viz-3/40 bg-warn-soft/40 p-3.5">
      <div className="flex items-start gap-2">
        <HelpCircle className="mt-0.5 size-4 shrink-0 text-warn" />
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-medium">Predict: what will the function return for this input?</div>
          {!answer ? (
            <form className="mt-2.5 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); const g = parseAnswer(guess); onAnswer({ correct: g.ok && answersMatch(g.value, trace.result, 'exact') }) }}>
              <input value={guess} onChange={(e) => setGuess(e.target.value)} placeholder="e.g. [1, 2]" className="w-44 rounded-lg border border-line bg-panel px-3 py-1.5 font-mono text-[13px] outline-none focus:border-accent" />
              <Button variant="outline" type="submit" disabled={!guess.trim()}>Check</Button>
              <Button variant="ghost" type="button" className="text-xs" onClick={() => onAnswer({ correct: null })}>Just show me</Button>
            </form>
          ) : (
            <div className="mt-2.5 flex flex-wrap items-center gap-3">
              <Verdict correct={answer.correct}>It returns <Mono>{formatJson(trace.result, 60)}</Mono></Verdict>
              <Button onClick={onContinue} className="py-1.5">See it <ChevronRight className="size-3.5" /></Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function Verdict({ correct, children }: { correct: boolean | null; children: ReactNode }) {
  return (
    <span className={clsx('inline-flex items-center gap-1.5 text-[13px]', correct === true ? 'text-ok' : correct === false ? 'text-bad' : 'text-muted')}>
      {correct === true && <Check className="size-4" strokeWidth={2.5} />}
      {correct === false && <X className="size-4" strokeWidth={2.5} />}
      <span className="text-ink">{correct === true ? 'Right. ' : correct === false ? 'Not quite. ' : ''}{children}</span>
    </span>
  )
}

function IconBtn({ label, onClick, disabled, children }: { label: string; onClick: () => void; disabled?: boolean; children: ReactNode }) {
  return (
    <button onClick={onClick} disabled={disabled} aria-label={label} title={label}
      className="flex size-8 items-center justify-center rounded-lg text-muted hover:bg-sunken hover:text-ink disabled:opacity-30">{children}</button>
  )
}
