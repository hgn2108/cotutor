import { useCallback, useState } from 'react'
import { Player } from '../../viz/Player'
import { useLesson } from '../context'
import { ContinueBar, Prose } from '../parts'

export function WatchChapter() {
  const { state, guided, record } = useLesson()
  const [progress, setProgress] = useState({ reachedEnd: false, answered: 0, total: 0 })
  const onProgress = useCallback((p: { reachedEnd: boolean; answered: number; correct: number; total: number }) => {
    setProgress(p)
    if (p.total) record('watch', { correct: p.correct, total: p.total })
  }, [record])
  return (
    <div>
      {guided && (
        <Prose className="mb-3 text-muted">
          Step through the solution on a small input. At the <span className="font-medium text-viz-3">●</span> checkpoints, predict what happens before you see it.
        </Prose>
      )}
      <Player trace={state.trace!} explanation={state.explanation} guided={guided} onProgress={onProgress} />
      <ContinueBar id="watch" enabled={progress.reachedEnd || (progress.total > 0 && progress.answered >= progress.total)} hint={guided && !progress.reachedEnd ? 'Step through to the end to continue.' : undefined} />
    </div>
  )
}
