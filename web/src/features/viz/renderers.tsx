import clsx from 'clsx'
import { AnimatePresence, motion } from 'motion/react'
import type { Snap } from '../../lib/types'
import { isObj, same, show } from './snap'

type Seq = { t: string; values: Snap[]; len: number }

const CELL = 46
const POINTER_COLORS = ['text-viz-1', 'text-viz-2', 'text-viz-3', 'text-viz-4']
const spring = { type: 'spring', stiffness: 420, damping: 32 } as const

function Label({ name, changed, note }: { name: string; changed?: boolean; note?: string }) {
  return (
    <div className="mb-1.5 flex items-baseline gap-2">
      <span className={clsx('font-mono text-[12.5px] font-semibold', changed ? 'text-accent' : 'text-ink')}>{name}</span>
      {note && <span className="text-[11px] text-faint">{note}</span>}
    </div>
  )
}

function Cell({ value, changed, dim, className }: { value: Snap; changed?: boolean; dim?: boolean; className?: string }) {
  return (
    <motion.div
      key={changed ? `c-${show(value)}` : undefined}
      initial={changed ? { scale: 0.8, opacity: 0.4 } : false}
      animate={{ scale: 1, opacity: 1 }} transition={spring}
      className={clsx(
        'flex h-10 items-center justify-center border font-mono text-[13px] tabular-nums',
        changed ? 'z-10 border-accent bg-accent-soft font-semibold text-accent' : 'border-line bg-panel',
        dim && 'opacity-40', className,
      )}
      style={{ width: CELL }}
    >
      {show(value, 6)}
    </motion.div>
  )
}

export interface Pointer { name: string; index: number }

export function ArrayView({ name, snap, prev, pointers }: { name: string; snap: Seq; prev?: Snap; pointers: Pointer[] }) {
  const values = snap.values as Snap[]
  const prevVals = isObj(prev ?? null) && 'values' in (prev as object) ? ((prev as { values: Snap[] }).values) : undefined
  const grew = prevVals && values.length > prevVals.length
  const byIndex = new Map<number, Pointer[]>()
  pointers.forEach((p) => byIndex.set(p.index, [...(byIndex.get(p.index) ?? []), p]))
  const rows = Math.max(0, ...[...byIndex.values()].map((ps) => ps.length))
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={`len ${snap.len}`} />
      <div className="overflow-x-auto pb-1">
        <div className="relative inline-block" style={{ paddingBottom: rows ? rows * 18 + 14 : 0 }}>
          <div className="flex">
            {values.length === 0 && <div className="flex h-10 items-center rounded border border-dashed border-line px-3 font-mono text-xs text-faint">empty</div>}
            {values.map((v, i) => (
              <div key={i} className="-ml-px first:ml-0">
                <Cell value={v} changed={!!prevVals && (i >= prevVals.length ? !!grew : !same(v, prevVals[i]))} className={clsx(i === 0 && 'rounded-l-md', i === values.length - 1 && 'rounded-r-md')} />
                <div className="mt-0.5 text-center font-mono text-[10px] text-faint">{i}</div>
              </div>
            ))}
          </div>
          {pointers.map((p) => {
            const stack = byIndex.get(p.index)!
            const row = stack.indexOf(p)
            const colorIdx = pointers.indexOf(p) % POINTER_COLORS.length
            const inRange = p.index >= 0 && p.index <= values.length
            if (!inRange) return null
            return (
              <motion.div
                key={p.name} layout transition={spring}
                className={clsx('absolute flex flex-col items-center font-mono text-[11px] font-semibold', POINTER_COLORS[colorIdx])}
                style={{ left: p.index * (CELL - 1) + CELL / 2 - 20, width: 40, top: 56 + row * 18 }}
              >
                {row === 0 && <span className="-mb-1 leading-none">▲</span>}
                <span className="leading-4">{p.name}</span>
              </motion.div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export function StackView({ name, snap, prev, horizontal }: { name: string; snap: Seq; prev?: Snap; horizontal?: boolean }) {
  const values = snap.values as Snap[]
  const prevLen = isObj(prev ?? null) && 'values' in (prev as object) ? (prev as { values: Snap[] }).values.length : values.length
  const items = values.map((v, i) => ({ v, i }))
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={horizontal ? 'front → back' : 'top ↑'} />
      <div className={clsx('flex gap-1', horizontal ? 'flex-row overflow-x-auto' : 'flex-col-reverse items-start')}>
        {values.length === 0 && <div className="flex h-9 items-center rounded-md border border-dashed border-line px-3 font-mono text-xs text-faint">empty</div>}
        <AnimatePresence initial={false}>
          {items.map(({ v, i }) => (
            <motion.div
              key={`${i}-${show(v)}`} layout initial={{ opacity: 0, y: horizontal ? 0 : -10, x: horizontal ? 10 : 0 }}
              animate={{ opacity: 1, y: 0, x: 0 }} exit={{ opacity: 0, scale: 0.8 }} transition={spring}
              className={clsx('flex h-9 min-w-[46px] items-center justify-center rounded-md border px-2.5 font-mono text-[13px]',
                i >= prevLen ? 'border-accent bg-accent-soft text-accent' : 'border-line bg-panel')}
            >{show(v, 14)}</motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function MapView({ name, snap, prev }: { name: string; snap: Extract<Snap, { t: 'dict' }>; prev?: Snap }) {
  const prevMap = new Map<string, string>()
  if (isObj(prev ?? null) && (prev as { t: string }).t === 'dict') (prev as Extract<Snap, { t: 'dict' }>).entries.forEach(([k, v]) => prevMap.set(show(k), show(v)))
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={`${snap.len} ${snap.len === 1 ? 'entry' : 'entries'}`} />
      <div className="flex flex-wrap gap-1.5">
        {snap.len === 0 && <div className="flex h-9 items-center rounded-md border border-dashed border-line px-3 font-mono text-xs text-faint">{'{ }'}</div>}
        <AnimatePresence initial={false}>
          {snap.entries.map(([k, v]) => {
            const key = show(k)
            const isNew = !!prev && !prevMap.has(key)
            const changed = !isNew && prevMap.has(key) && prevMap.get(key) !== show(v)
            return (
              <motion.div
                key={key} layout initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.7 }} transition={spring}
                className={clsx('flex h-9 items-stretch overflow-hidden rounded-md border font-mono text-[12.5px]',
                  isNew ? 'border-ok ring-2 ring-ok/25' : changed ? 'border-warn ring-2 ring-warn/25' : 'border-line')}
              >
                <span className="flex items-center bg-sunken px-2 font-semibold">{show(k, 14)}</span>
                <span className="flex items-center bg-panel px-2 text-muted">{show(v, 18)}</span>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function SetView({ name, snap, prev }: { name: string; snap: Seq; prev?: Snap }) {
  const before = new Set(isObj(prev ?? null) && 'values' in (prev as object) ? (prev as { values: Snap[] }).values.map((v) => show(v)) : [])
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={`${snap.len} items`} />
      <div className="flex flex-wrap gap-1.5">
        {snap.len === 0 && <div className="flex h-8 items-center rounded-full border border-dashed border-line px-3 font-mono text-xs text-faint">empty</div>}
        <AnimatePresence initial={false}>
          {(snap.values as Snap[]).map((v) => (
            <motion.span key={show(v)} layout initial={{ opacity: 0, scale: 0.6 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.6 }} transition={spring}
              className={clsx('flex h-8 items-center rounded-full border px-3 font-mono text-[12.5px]', prev && !before.has(show(v)) ? 'border-ok bg-ok-soft text-ok' : 'border-line bg-panel')}>
              {show(v, 14)}
            </motion.span>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function GridView({ name, snap, prev, cursor }: { name: string; snap: Seq; prev?: Snap; cursor?: [number, number] }) {
  const rows = (snap.values as Snap[]).map((r) => (isObj(r) && 'values' in r ? (r.values as Snap[]) : [r]))
  const prevRows = isObj(prev ?? null) && 'values' in (prev as object)
    ? (prev as { values: Snap[] }).values.map((r) => (isObj(r) && 'values' in r ? (r.values as Snap[]) : [r])) : undefined
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={`${rows.length} × ${rows[0]?.length ?? 0}`} />
      <div className="overflow-x-auto">
        <table className="border-separate border-spacing-0 font-mono text-[12.5px]">
          <thead><tr><th />{rows[0]?.map((_, j) => <th key={j} className="px-1 pb-0.5 text-[10px] font-normal text-faint">{j}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td className="pr-1.5 text-right text-[10px] text-faint">{i}</td>
                {row.map((v, j) => {
                  const changed = prevRows && !same(v, prevRows[i]?.[j])
                  const here = cursor && cursor[0] === i && cursor[1] === j
                  return (
                    <td key={j} className="p-0">
                      <motion.div
                        key={changed ? show(v) : 'same'} initial={changed ? { backgroundColor: 'var(--color-accent-soft)' } : false}
                        animate={{ backgroundColor: changed ? 'var(--color-accent-soft)' : 'var(--color-panel)' }}
                        className={clsx('-ml-px -mt-px flex h-9 min-w-[40px] items-center justify-center border px-1.5 tabular-nums',
                          here ? 'relative z-10 border-accent ring-2 ring-accent/40' : 'border-line', changed && 'font-semibold text-accent')}
                      >{show(v, 5)}</motion.div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function LinkedView({ name, snap, prev }: { name: string; snap: Extract<Snap, { t: 'linked' }>; prev?: Snap }) {
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} />
      <div className="flex flex-wrap items-center gap-y-2 overflow-x-auto">
        {snap.values.length === 0 && <span className="font-mono text-xs text-faint">None</span>}
        <AnimatePresence initial={false}>
          {snap.values.map((v, i) => (
            <motion.div key={`${i}-${show(v)}`} layout initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={spring} className="flex items-center">
              <div className={clsx('flex h-9 min-w-[40px] items-center justify-center rounded-md border px-2 font-mono text-[13px]', i === 0 ? 'border-accent bg-accent-soft text-accent' : 'border-line bg-panel')}>{show(v, 6)}</div>
              <span className="px-1 text-faint">{i === snap.values.length - 1 ? '→ ∅' : '→'}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}

export function TreeView({ name, snap, prev }: { name: string; snap: Extract<Snap, { t: 'tree' }>; prev?: Snap }) {
  // Place level-order values into heap positions, then lay out by depth.
  const values = snap.values
  const nodes: { v: number | string; x: number; y: number; parent?: { x: number; y: number } }[] = []
  const pos = new Map<number, { x: number; y: number }>()
  let idx = 0
  const queue: { slot: number; depth: number; lo: number; hi: number }[] = values.length && values[0] !== null ? [{ slot: 0, depth: 0, lo: 0, hi: 1 }] : []
  const parentOf = new Map<number, number>()
  let depthMax = 0
  while (queue.length && idx < values.length) {
    const cur = queue.shift()!
    const v = values[idx++]
    if (v === null) continue
    const x = (cur.lo + cur.hi) / 2
    pos.set(cur.slot, { x, y: cur.depth })
    depthMax = Math.max(depthMax, cur.depth)
    const p = parentOf.get(cur.slot)
    nodes.push({ v, x, y: cur.depth, parent: p !== undefined ? pos.get(p) : undefined })
    const mid = (cur.lo + cur.hi) / 2
    for (const [slot, lo, hi] of [[cur.slot * 2 + 1, cur.lo, mid], [cur.slot * 2 + 2, mid, cur.hi]] as const) {
      parentOf.set(slot, cur.slot)
      queue.push({ slot, depth: cur.depth + 1, lo, hi })
    }
  }
  const W = Math.max(160, Math.min(520, 2 ** depthMax * 44)), LH = 52, R = 15
  return (
    <div>
      <Label name={name} changed={!same(snap, prev)} note={`${nodes.length} nodes`} />
      {nodes.length === 0 ? <span className="font-mono text-xs text-faint">None</span> : (
        <svg width={W} height={(depthMax + 1) * LH} className="max-w-full overflow-visible">
          {nodes.map((n, i) => n.parent && (
            <line key={`e${i}`} x1={n.parent.x * W} y1={n.parent.y * LH + R + 4} x2={n.x * W} y2={n.y * LH + R + 4} className="stroke-line" strokeWidth={1.5} />
          ))}
          {nodes.map((n, i) => (
            <g key={i} transform={`translate(${n.x * W},${n.y * LH + R + 4})`}>
              <circle r={R} className={i === 0 ? 'fill-accent-soft stroke-accent' : 'fill-panel stroke-line'} strokeWidth={1.5} />
              <text textAnchor="middle" dy={4} className={clsx('font-mono text-[12px]', i === 0 ? 'fill-accent font-semibold' : 'fill-ink')}>{String(n.v).slice(0, 4)}</text>
            </g>
          ))}
        </svg>
      )}
    </div>
  )
}

export function ScalarsView({ items }: { items: { name: string; value: Snap; changed: boolean }[] }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map(({ name, value, changed }) => (
        <motion.div
          key={name + (changed ? show(value) : '')} initial={changed ? { scale: 0.9 } : false} animate={{ scale: 1 }} transition={spring}
          className={clsx('flex h-8 items-stretch overflow-hidden rounded-md border font-mono text-[12.5px]', changed ? 'border-accent' : 'border-line')}
        >
          <span className="flex items-center bg-sunken px-2 text-muted">{name}</span>
          <span className={clsx('flex items-center px-2', changed ? 'bg-accent-soft font-semibold text-accent' : 'bg-panel')}>{show(value, 24)}</span>
        </motion.div>
      ))}
    </div>
  )
}
