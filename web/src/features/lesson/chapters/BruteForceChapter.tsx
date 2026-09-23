import { Check } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '../../../components/ui'
import { CodeView } from '../../viz/CodeView'
import { useLesson } from '../context'
import { Callout, ContinueBar, Prose, ThinkFirst } from '../parts'

export function BruteForceChapter() {
  const { state } = useLesson()
  const intro = state.lessonIntro!
  const [revealed, setRevealed] = useState(false)
  return (
    <div>
      <ThinkFirst
        prompt="Forget efficiency. What's the most direct way to get the right answer?"
        placeholder="e.g. check every possible…" revealLabel="Show the brute force"
        revealed={revealed} onReveal={() => setRevealed(true)}
      >
        <Prose>{intro.brute_force_idea}</Prose>
        <div className="mt-3"><CodeView code={intro.brute_force_code} maxHeight={360} /></div>
        <div className="mt-3 flex flex-wrap items-baseline gap-2 text-[13.5px]">
          <Badge tone="warn" className="font-mono text-[12px]">{intro.brute_force_time}</Badge>
          <span className="text-muted">{intro.brute_force_why}</span>
        </div>
        {intro.brute_is_optimal && (
          <Callout tone="ok" className="mt-3" icon={<Check className="size-4" />}>
            Measured: for this problem the direct approach already grows as slowly as it can. Sometimes the obvious solution is the optimal one, and the skill is recognizing that.
          </Callout>
        )}
        {state.oracle && !state.oracle.trusted && (
          <p className="mt-2 text-xs text-warn">Heads up: this brute force disagreed with one of the examples during verification, so treat it as a sketch.</p>
        )}
      </ThinkFirst>
      <ContinueBar id="brute" enabled={revealed} />
    </div>
  )
}
