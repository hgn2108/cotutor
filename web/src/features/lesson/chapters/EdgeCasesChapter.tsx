import { useMemo, useState } from 'react'
import { Badge, Button, formatJson } from '../../../components/ui'
import type { CaseDef, CaseResult, Json } from '../../../lib/types'
import { Verdict } from '../../viz/Player'
import { answersMatch, parseAnswer } from '../answers'
import { useLesson } from '../context'
import { ArgsInline, ContinueBar, Prose } from '../parts'

interface EdgeItem { def: CaseDef; result: CaseResult }

/** Agent ids like `tricky_equal_hours` read as "Tricky equal hours". */
function humanize(label: string): string {
  if (!/^[a-z0-9]+(_[a-z0-9]+)+$/i.test(label)) return label
  const s = label.replace(/_/g, ' ')
  return s[0].toUpperCase() + s.slice(1)
}

function pickEdgeCases(defs: CaseDef[], results: CaseResult[], design: boolean): EdgeItem[] {
  const byId = new Map(results.map((r) => [r.id, r]))
  const usable = defs
    .map((def) => ({ def, result: byId.get(def.id)! }))
    .filter((x) => x.result && x.result.expected_source !== 'none' && x.def.source !== 'stress' && x.def.category !== 'large'
      && (!design || (Array.isArray(x.result.expected) && x.result.expected.slice(1).some((v) => v !== null)))
      && JSON.stringify(x.def.args).length < (design ? 220 : 90))
  const rank = (x: EdgeItem) => (x.def.category === 'tricky' ? 0 : x.def.category === 'edge' ? 1 : 2)
  // Prefer inputs the learner hasn't already seen as examples in step 1.
  const fresh = usable.filter((x) => x.def.source !== 'example')
  const pool = fresh.length >= 3 ? fresh : usable
  return pool.sort((a, b) => rank(a) - rank(b)).slice(0, 4)
}

function EdgeCase({ item, index, onResult }: { item: EdgeItem; index: number; onResult: (correct: boolean | null) => void }) {
  const { state, guided, isDone } = useLesson()
  const spec = state.spec
  const design = spec?.kind === 'design'
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12px] font-semibold text-faint">#{index + 1}</span>
        <span className="text-[13.5px] font-medium">{humanize(item.def.label)}</span>
        {item.def.category && <Badge>{item.def.category}</Badge>}
      </div>
      {design
        ? <DesignPrediction item={item} guided={guided && !isDone('edges')} onResult={onResult} />
        : <ValuePrediction item={item} guided={guided && !isDone('edges')} onResult={onResult} />}
      {item.def.rationale && <p className="mt-2 text-[12.5px] leading-relaxed text-muted">Why it matters: {item.def.rationale}</p>}
    </div>
  )
}

/** Predict a function's return value. */
function ValuePrediction({ item, guided, onResult }: { item: EdgeItem; guided: boolean; onResult: (correct: boolean | null) => void }) {
  const { state } = useLesson()
  const spec = state.spec
  const [guess, setGuess] = useState('')
  const [outcome, setOutcome] = useState<boolean | null | undefined>(undefined)
  const expected = item.result.expected as Json
  const check = () => {
    const g = parseAnswer(guess)
    const ok = g.ok && answersMatch(g.value, expected, spec?.comparison ?? 'exact')
    setOutcome(ok)
    onResult(ok)
  }
  return (
    <>
      <div className="mt-2"><ArgsInline args={item.def.args} spec={spec} /></div>
      {guided && outcome === undefined ? (
        <form className="mt-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); check() }}>
          <input value={guess} onChange={(e) => setGuess(e.target.value)} placeholder="Your predicted output"
            className="w-56 max-w-full rounded-lg border border-line bg-sunken px-3 py-1.5 font-mono text-[13px] outline-none focus:border-accent" />
          <Button variant="outline" type="submit" disabled={!guess.trim()}>Check</Button>
          <Button variant="ghost" type="button" className="text-xs" onClick={() => { setOutcome(null); onResult(null) }}>Reveal</Button>
        </form>
      ) : outcome !== undefined ? (
        <div className="mt-3">
          <Verdict correct={outcome}>{outcome === false && <>You said <code className="font-mono">{guess.trim()}</code> · </>}Expected <code className="font-mono">{formatJson(expected)}</code>{spec?.multiple_valid_answers && outcome === false ? ' (other answers can also be valid here)' : ''}</Verdict>
        </div>
      ) : (
        <div className="mt-3 text-[13px]"><span className="text-muted">Output: </span><code className="font-mono font-semibold">{formatJson(expected)}</code></div>
      )}
    </>
  )
}

/** Design problems: predict what each call returns, one call at a time. */
function DesignPrediction({ item, guided, onResult }: { item: EdgeItem; guided: boolean; onResult: (correct: boolean | null) => void }) {
  const [ops, opArgs] = item.def.args as [Json[], Json[][]]
  const expected = (Array.isArray(item.result.expected) ? item.result.expected : []) as Json[]
  // Calls that return something are the questions; constructors and updates just set the scene.
  const asked = ops.map((_, k) => k).filter((k) => k > 0 && expected[k] !== null && expected[k] !== undefined)
  const [guesses, setGuesses] = useState<Record<number, string>>({})
  const [checked, setChecked] = useState<Record<number, boolean> | null>(null)
  const [revealed, setRevealed] = useState(false)
  const showAnswers = !guided || checked !== null || revealed
  const check = () => {
    const res = Object.fromEntries(asked.map((k) => {
      const g = parseAnswer(guesses[k] ?? '')
      return [k, g.ok && answersMatch(g.value, expected[k], 'exact')]
    }))
    setChecked(res)
    onResult(asked.every((k) => res[k]))
  }
  return (
    <form className="mt-2" onSubmit={(e) => { e.preventDefault(); check() }}>
      <ol className="grid gap-1 font-mono text-[12.5px]">
        {ops.map((op, k) => (
          <li key={k} className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className={k === 0 ? 'font-semibold' : ''}>{String(op)}<span className="text-muted">({(opArgs[k] ?? []).map((a) => formatJson(a, 30)).join(', ')})</span></span>
            {asked.includes(k) && (
              <>
                <span className="text-faint">→</span>
                {showAnswers ? (
                  <span className={checked ? (checked[k] ? 'text-ok' : 'text-bad') : 'font-semibold'}>
                    {checked && !checked[k] && guesses[k]?.trim() && <span className="line-through opacity-70">{guesses[k].trim()}</span>} {formatJson(expected[k], 40)}
                  </span>
                ) : (
                  <input value={guesses[k] ?? ''} onChange={(e) => setGuesses({ ...guesses, [k]: e.target.value })} aria-label={`What does ${String(op)} return?`}
                    className="w-24 rounded-md border border-line bg-sunken px-2 py-0.5 outline-none focus:border-accent" placeholder="?" />
                )}
              </>
            )}
          </li>
        ))}
      </ol>
      {guided && !showAnswers && asked.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="outline" type="submit" disabled={asked.some((k) => !guesses[k]?.trim())}>Check</Button>
          <Button variant="ghost" type="button" className="text-xs" onClick={() => { setRevealed(true); onResult(null) }}>Reveal</Button>
        </div>
      )}
      {checked && <div className="mt-2"><Verdict correct={asked.every((k) => checked[k])}>{asked.filter((k) => checked[k]).length} of {asked.length} calls predicted.</Verdict></div>}
    </form>
  )
}

export function EdgeCasesChapter() {
  const { state, guided, record } = useLesson()
  const last = state.verifications.at(-1)!
  const items = useMemo(() => pickEdgeCases(last.cases, last.results, state.spec?.kind === 'design'), [last, state.spec?.kind])
  const [results, setResults] = useState<Record<number, boolean | null>>({})
  const answered = Object.keys(results).length
  const set = (k: number, v: boolean | null) => {
    const next = { ...results, [k]: v }
    setResults(next)
    record('edges', { correct: Object.values(next).filter(Boolean).length, total: items.length })
  }
  if (!items.length) return <div><Prose className="text-muted">No small edge cases to practice on for this problem.</Prose><ContinueBar id="edges" enabled /></div>
  return (
    <div>
      <Prose className="mb-3 text-muted">
        {guided ? 'Predict what the solution returns for each tricky input. These are the cases that break sloppy solutions.' : 'Tricky inputs that break sloppy solutions, with their correct outputs.'}
      </Prose>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((it, k) => <EdgeCase key={it.def.id} item={it} index={k} onResult={(v) => set(k, v)} />)}
      </div>
      <ContinueBar id="edges" enabled={answered >= items.length} hint={guided && answered < items.length ? `${answered}/${items.length} answered` : undefined} />
    </div>
  )
}
