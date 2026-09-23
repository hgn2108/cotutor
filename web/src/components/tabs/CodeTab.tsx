import { DiffEditor, Editor } from '@monaco-editor/react'
import { Check, Copy } from 'lucide-react'
import { useState } from 'react'
import type { RunState } from '../../lib/useRun'
import { Badge, Button, Card, SectionTitle, Waiting } from '../ui'

const editorOptions = {
  readOnly: true, minimap: { enabled: false }, fontSize: 13, fontFamily: 'JetBrains Mono, monospace',
  lineNumbersMinChars: 3, scrollBeyondLastLine: false, renderLineHighlight: 'none' as const,
  padding: { top: 12, bottom: 12 }, scrollbar: { alwaysConsumeMouseWheel: false },
}

function heightFor(code: string) {
  return Math.min(560, Math.max(160, code.split('\n').length * 19 + 32))
}

export function CodeTab({ state, dark }: { state: RunState; dark: boolean }) {
  const solution = state.solutions.at(-1)
  const [copied, setCopied] = useState(false)
  if (!solution) return <Waiting label="Waiting for the solver…" />
  const verified = state.summary?.verified
  const copy = async () => {
    await navigator.clipboard.writeText(solution.code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="grid gap-4">
      <Card className="overflow-hidden">
        <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
          <span className="font-mono text-xs text-muted">solution.py</span>
          {solution.revision > 0 && <Badge tone="warn">revision {solution.revision}</Badge>}
          {verified === true && <Badge tone="ok">verified</Badge>}
          {verified === false && <Badge tone="bad">failed verification</Badge>}
          <Button variant="ghost" className="ml-auto text-xs" onClick={copy}>
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}{copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
        <Editor height={heightFor(solution.code)} language="python" value={solution.code} theme={dark ? 'vs-dark' : 'light'} options={editorOptions} />
      </Card>

      {state.debugAttempts.map((d) => (
        <Card key={d.attempt} className="overflow-hidden">
          <div className="border-b border-line px-4 py-3">
            <SectionTitle aside={<Badge tone="warn">fix #{d.attempt}</Badge>}>Debugger</SectionTitle>
            <p className="text-[13.5px] leading-relaxed"><span className="font-medium">Diagnosis: </span>{d.diagnosis}</p>
            <p className="mt-1 text-[13px] text-muted"><span className="font-medium text-ink">Fix: </span>{d.fix_summary}</p>
          </div>
          <DiffEditor
            height={heightFor(`${d.before}\n${d.after}`)} language="python" original={d.before} modified={d.after}
            theme={dark ? 'vs-dark' : 'light'}
            options={{ ...editorOptions, renderSideBySide: false, renderOverviewRuler: false }}
          />
        </Card>
      ))}
    </div>
  )
}
