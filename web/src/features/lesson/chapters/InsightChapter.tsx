import { Editor } from '@monaco-editor/react'
import { Check, Copy, Lightbulb } from 'lucide-react'
import { useState } from 'react'
import { Flowchart } from '../../../components/Flowchart'
import { Badge, Button, Card } from '../../../components/ui'
import { useLesson } from '../context'
import { Callout, ContinueBar, ThinkFirst } from '../parts'

export function InsightChapter() {
  const { state, dark } = useLesson()
  const solution = state.solutions.at(-1)!
  const ex = state.explanation
  const [revealed, setRevealed] = useState(false)
  const [copied, setCopied] = useState(false)
  return (
    <div>
      <ThinkFirst
        prompt="You know where the wasted work is. How could you avoid repeating it?"
        placeholder="e.g. remember something so you don't have to search again…" revealLabel="Show the key insight"
        revealed={revealed} onReveal={() => setRevealed(true)}
      >
        <Callout icon={<Lightbulb className="size-4" />} title={solution.approach}>
          {state.lessonDeep?.insight ?? solution.key_insight}
          {ex?.intuition && <p className="mt-1.5 text-muted">{ex.intuition}</p>}
        </Callout>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-line px-4 py-2">
              <span className="font-mono text-xs text-muted">solution.py</span>
              {state.summary?.verified && <Badge tone="ok">verified</Badge>}
              <Button variant="ghost" className="ml-auto text-xs" onClick={async () => { await navigator.clipboard.writeText(solution.code); setCopied(true); setTimeout(() => setCopied(false), 1500) }}>
                {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}{copied ? 'Copied' : 'Copy'}
              </Button>
            </div>
            <Editor
              height={Math.min(460, solution.code.split('\n').length * 19 + 28)} language="python" value={solution.code} theme={dark ? 'vs-dark' : 'light'}
              options={{ readOnly: true, minimap: { enabled: false }, fontSize: 13, fontFamily: 'JetBrains Mono, monospace', lineNumbersMinChars: 3, scrollBeyondLastLine: false, renderLineHighlight: 'none', padding: { top: 10, bottom: 10 }, scrollbar: { alwaysConsumeMouseWheel: false } }}
            />
          </Card>
          {ex && (
            <Card className="p-4">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Control flow</div>
              <Flowchart nodes={ex.flow_nodes} edges={ex.flow_edges} />
            </Card>
          )}
        </div>
        <details className="mt-3 rounded-xl border border-line bg-panel">
          <summary className="cursor-pointer select-none px-4 py-2.5 text-[13px] font-medium text-muted hover:text-ink">The reasoning, step by step</summary>
          <ol className="grid gap-3 border-t border-line p-4">
            {solution.steps.map((s, k) => (
              <li key={k} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-sunken font-mono text-[11px] font-semibold text-muted">{k + 1}</span>
                <div><div className="text-[13.5px] font-medium">{s.title}</div><p className="mt-0.5 text-[13px] leading-relaxed text-muted">{s.detail}</p></div>
              </li>
            ))}
          </ol>
        </details>
      </ThinkFirst>
      <ContinueBar id="insight" enabled={revealed} />
    </div>
  )
}
