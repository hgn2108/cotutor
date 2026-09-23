import { useMemo, useState } from 'react'
import { Badge, Button, formatJson } from '../../../components/ui'
import type { CaseDef, CaseResult, Json } from '../../../lib/types'
import { Verdict } from '../../viz/Player'
import { answersMatch, parseAnswer } from '../answers'
import { useLesson } from '../context'
import { ArgsInline, ContinueBar, Prose } from '../parts'

interface EdgeItem { def: CaseDef; result: CaseResult }

function pickEdgeCases(defs: CaseDef[], results: CaseResult[]): EdgeItem[] {
  const byId = new Map(results.map((r) => [r.id, r]))
  const usable = defs
    .map((def) => ({ def, result: byId.get(def.id)! }))
    .filter((x) => x.result && x.result.expected_source !== 'none' && x.def.source !== 'stress' && x.def.category !== 'large'
      && JSON.stringify(x.def.args).length < 90)
  const rank = (x: EdgeItem) => (x.def.category === 'tricky' ? 0 : x.def.category === 'edge' ? 1 : 2)
  return usable.sort((a, b) => rank(a) - rank(b)).slice(0, 4)
}

function EdgeCase({ item, index, onResult }: { item: EdgeItem; index: number; onResult: (correct: boolean | null) => void }) {
  const { state, guided } = useLesson()
  const spec = state.spec
  const [guess, setGuess] = useState('')
  const [outcome, setOutcome] = useState<boolean | null | undefined>(undefined)
  const expected = item.result.expected as Json
  const multi = spec?.multiple_valid_answers
  const done = !guided || outcome !== undefined
  const check = () => {
    const g = parseAnswer(guess)
    const ok = g.ok && answersMatch(g.value, expected, spec?.comparison ?? 'exact')
    setOutcome(ok)
    onResult(ok)
  }
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[12px] font-semibold text-faint">#{index + 1}</span>
        <span className="text-[13.5px] font-medium">{item.def.label}</span>
        {item.def.category && <Badge>{item.def.category}</Badge>}
      </div>
      <div className="mt-2"><ArgsInline args={item.def.args} spec={spec} /></div>
      {!done ? (
        <form className="mt-3 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); check() }}>
          <input value={guess} onChange={(e) => setGuess(e.target.value)} placeholder="Your predicted output"
            className="w-56 rounded-lg border border-line bg-sunken px-3 py-1.5 font-mono text-[13px] outline-none focus:border-accent" />
          <Button variant="outline" type="submit" disabled={!guess.trim()}>Check</Button>
          <Button variant="ghost" type="button" className="text-xs" onClick={() => { setOutcome(null); onResult(null) }}>Reveal</Button>
        </form>
      ) : (
        <div className="mt-3 grid gap-1.5">
          {guided
            ? <Verdict correct={outcome ?? null}>Expected <code className="font-mono">{formatJson(expected)}</code>{multi && outcome === false ? ' (other answers can also be valid here)' : ''}</Verdict>
            : <div className="text-[13px]"><span className="text-muted">Output: </span><code className="font-mono font-semibold">{formatJson(expected)}</code></div>}
          {item.def.rationale && <p className="text-[12.5px] leading-relaxed text-muted">Why it matters: {item.def.rationale}</p>}
        </div>
      )}
    </div>
  )
}

export function EdgeCasesChapter() {
  const { state, guided, record } = useLesson()
  const last = state.verifications.at(-1)!
  const items = useMemo(() => pickEdgeCases(last.cases, last.results), [last])
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
