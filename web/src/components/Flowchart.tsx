import { Graph, layout } from '@dagrejs/dagre'
import clsx from 'clsx'
import { useMemo, useState } from 'react'
import type { FlowEdge, FlowNode } from '../lib/types'

const CHAR_W = 7.2
const NODE_H = 40

interface Laid {
  nodes: (FlowNode & { x: number; y: number; w: number; h: number })[]
  edges: (FlowEdge & { points: { x: number; y: number }[]; lx?: number; ly?: number; back: boolean })[]
  width: number
  height: number
}

function computeLayout(nodes: FlowNode[], edges: FlowEdge[]): Laid {
  const g = new Graph({ multigraph: true })
  g.setGraph({ rankdir: 'TB', nodesep: 36, ranksep: 46, edgesep: 18, marginx: 12, marginy: 12 })
  g.setDefaultEdgeLabel(() => ({}))
  const ids = new Set(nodes.map((n) => n.id))
  const order = new Map(nodes.map((n, i) => [n.id, i]))
  for (const n of nodes) {
    const w = Math.max(96, Math.min(240, n.label.length * CHAR_W + 44))
    g.setNode(n.id, { width: w, height: NODE_H })
  }
  const kept = edges.filter((e) => ids.has(e.source) && ids.has(e.target))
  kept.forEach((e, i) => {
    // Edges pointing "up" the declared order are loop-backs; letting dagre reverse them keeps
    // the main flow reading top-to-bottom.
    const back = (order.get(e.target) ?? 0) <= (order.get(e.source) ?? 0)
    g.setEdge(e.source, e.target, { width: e.label ? e.label.length * 6.5 + 10 : 0, height: e.label ? 16 : 0, labelpos: 'c', weight: back ? 0 : 2 }, `e${i}`)
  })
  layout(g)
  const laidNodes = nodes.map((n) => {
    const v = g.node(n.id) as { x: number; y: number; width: number; height: number }
    return { ...n, x: v.x, y: v.y, w: v.width, h: v.height }
  })
  const laidEdges = kept.map((e, i) => {
    const v = g.edge({ v: e.source, w: e.target, name: `e${i}` }) as { points: { x: number; y: number }[]; x?: number; y?: number }
    const back = (order.get(e.target) ?? 0) <= (order.get(e.source) ?? 0)
    return { ...e, points: v.points, lx: v.x, ly: v.y, back }
  })
  const graph = g.graph() as { width?: number; height?: number }
  return { nodes: laidNodes, edges: laidEdges, width: graph.width ?? 400, height: graph.height ?? 300 }
}

/** Cubic B-spline through dagre's control points (same curve as d3.curveBasis). */
function basisPath(pts: { x: number; y: number }[]): string {
  if (pts.length < 3) return `M${pts.map((p) => `${p.x},${p.y}`).join('L')}`
  let d = `M${pts[0].x},${pts[0].y}L${(5 * pts[0].x + pts[1].x) / 6},${(5 * pts[0].y + pts[1].y) / 6}`
  for (let i = 1; i < pts.length - 1; i++) {
    const [p0, p1, p2] = [pts[i - 1], pts[i], pts[i + 1]]
    d += `C${(2 * p0.x + p1.x) / 3},${(2 * p0.y + p1.y) / 3} ${(p0.x + 2 * p1.x) / 3},${(p0.y + 2 * p1.y) / 3} ${(p0.x + 4 * p1.x + p2.x) / 6},${(p0.y + 4 * p1.y + p2.y) / 6}`
  }
  const [a, b] = [pts[pts.length - 2], pts[pts.length - 1]]
  d += `C${(2 * a.x + b.x) / 3},${(2 * a.y + b.y) / 3} ${(a.x + 5 * b.x) / 6},${(a.y + 5 * b.y) / 6} ${b.x},${b.y}`
  return d
}

const kindStyle: Record<FlowNode['kind'], string> = {
  start: 'fill-sunken stroke-line',
  end: 'fill-ok-soft stroke-ok/50',
  step: 'fill-panel stroke-line',
  decision: 'fill-warn-soft stroke-warn/60',
  loop: 'fill-accent-soft stroke-accent/60',
}

export function Flowchart({ nodes, edges }: { nodes: FlowNode[]; edges: FlowEdge[] }) {
  const laid = useMemo(() => computeLayout(nodes, edges), [nodes, edges])
  const [hover, setHover] = useState<string | null>(null)
  const hovered = laid.nodes.find((n) => n.id === hover)

  return (
    <div className="relative">
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${laid.width} ${laid.height}`} width={laid.width} height={laid.height} className="mx-auto block max-w-full" role="img" aria-label="Algorithm flowchart">
          <defs>
            <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="fill-faint" />
            </marker>
            <marker id="arrow-back" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="fill-accent" />
            </marker>
          </defs>
          {laid.edges.map((e, i) => {
            const active = hover && (e.source === hover || e.target === hover)
            return (
              <g key={i}>
                <path
                  d={basisPath(e.points)} fill="none" markerEnd={`url(#${e.back ? 'arrow-back' : 'arrow'})`}
                  className={clsx('transition-opacity', e.back ? 'stroke-accent' : 'stroke-faint', hover && !active && 'opacity-30')}
                  strokeWidth={active ? 2 : 1.4} strokeDasharray={e.back ? '5 4' : undefined}
                />
                {e.label && e.lx !== undefined && e.ly !== undefined && (
                  <g transform={`translate(${e.lx},${e.ly})`}>
                    <rect x={-(e.label.length * 6.5 + 10) / 2} y={-9} width={e.label.length * 6.5 + 10} height={18} rx={9} className="fill-bg stroke-line" />
                    <text textAnchor="middle" dy={4} className={clsx('text-[10.5px] font-medium', e.back ? 'fill-accent' : 'fill-muted')}>{e.label}</text>
                  </g>
                )}
              </g>
            )
          })}
          {laid.nodes.map((n) => {
            const pill = n.kind === 'start' || n.kind === 'end'
            return (
              <g key={n.id} transform={`translate(${n.x - n.w / 2},${n.y - n.h / 2})`}
                onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)} className="cursor-default">
                {n.kind === 'decision' ? (
                  <polygon points={`12,0 ${n.w - 12},0 ${n.w},${n.h / 2} ${n.w - 12},${n.h} 12,${n.h} 0,${n.h / 2}`} className={clsx(kindStyle[n.kind], 'stroke-[1.4]')} />
                ) : (
                  <rect width={n.w} height={n.h} rx={pill ? n.h / 2 : 9} className={clsx(kindStyle[n.kind], 'stroke-[1.4]', hover === n.id && 'stroke-accent')} />
                )}
                {n.kind === 'loop' && <text x={10} y={n.h / 2 + 4} className="fill-accent text-[12px]">↻</text>}
                <text x={n.w / 2 + (n.kind === 'loop' ? 5 : 0)} y={n.h / 2 + 4} textAnchor="middle" className="fill-ink text-[12.5px] font-medium">{n.label}</text>
              </g>
            )
          })}
        </svg>
      </div>
      <div className="mt-2 min-h-[20px] text-center text-[12.5px] text-muted">
        {hovered?.detail ? hovered.detail : <span className="text-faint">Hover a step for details · dashed arrows loop back</span>}
      </div>
    </div>
  )
}
