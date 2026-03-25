import { useMemo } from 'react'
import { Agent } from '../types/agent'

/* ══════════════════════════════════════════════
   WorkflowDAG — 代理協作流程視覺化
   以 DAG（有向無環圖）方式呈現任務流程中的代理互動。
   ══════════════════════════════════════════════ */

interface DAGNode {
  id: string
  label: string
  status: 'idle' | 'working' | 'waiting' | 'completed' | 'error'
  tier: string
  progress?: number
  task?: string
}

interface DAGEdge {
  from: string
  to: string
  label?: string
}

interface Props {
  agents: Agent[]
  title?: string
}

/* ── Status colors and icons ── */
const STATUS_COLORS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  idle: { bg: '#1e293b', border: '#475569', text: '#94a3b8', glow: 'none' },
  working: { bg: '#064e3b', border: '#10b981', text: '#6ee7b7', glow: '0 0 12px rgba(16,185,129,0.4)' },
  waiting: { bg: '#422006', border: '#f59e0b', text: '#fcd34d', glow: '0 0 12px rgba(245,158,11,0.3)' },
  completed: { bg: '#1e1b4b', border: '#6366f1', text: '#a5b4fc', glow: '0 0 8px rgba(99,102,241,0.3)' },
  error: { bg: '#450a0a', border: '#ef4444', text: '#fca5a5', glow: '0 0 12px rgba(239,68,68,0.4)' },
}

const TIER_COLORS: Record<string, string> = {
  leadership: '#f59e0b',
  data: '#10b981',
  'ai-ml': '#8b5cf6',
  domain: '#ec4899',
  engineering: '#f97316',
  research: '#06b6d4',
}

export default function WorkflowDAG({ agents, title }: Props) {
  // Build DAG from active agents
  const { nodes, edges, activeCount } = useMemo(() => {
    const workingAgents = agents.filter(
      (a) => a.status === 'working' || a.status === 'waiting' || a.status === 'completed'
    )
    // Build nodes from active agents
    const dagNodes: DAGNode[] = workingAgents.map((a) => ({
      id: a.id,
      label: a.displayName,
      status: a.status,
      tier: a.tier,
      progress: a.progress,
      task: a.currentTask,
    }))

    // Build edges based on collaboration and tier hierarchy
    const dagEdges: DAGEdge[] = []

    // Director → working agents
    const director = workingAgents.find((a) => a.tier === 'leadership')
    if (director) {
      workingAgents
        .filter((a) => a.tier !== 'leadership')
        .forEach((a) => {
          dagEdges.push({ from: director.id, to: a.id, label: '指派' })
        })
    }

    // Collaboration edges
    workingAgents.forEach((a) => {
      a.collaboratingWith?.forEach((partnerId) => {
        if (workingAgents.some((w) => w.id === partnerId)) {
          dagEdges.push({ from: a.id, to: partnerId, label: '協作' })
        }
      })
    })

    return {
      nodes: dagNodes,
      edges: dagEdges,
      activeCount: workingAgents.length,
    }
  }, [agents])

  // Layout — arrange nodes in columns by tier
  const layout = useMemo(() => {
    const tierOrder = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']
    const tiers: Record<string, DAGNode[]> = {}

    nodes.forEach((n) => {
      if (!tiers[n.tier]) tiers[n.tier] = []
      tiers[n.tier].push(n)
    })

    const positions: Record<string, { x: number; y: number }> = {}
    const activeTiers = tierOrder.filter((t) => tiers[t]?.length)
    const totalCols = activeTiers.length || 1
    const colWidth = 100 / (totalCols + 1)

    activeTiers.forEach((tier, colIdx) => {
      const tierNodes = tiers[tier]
      const rowHeight = 100 / (tierNodes.length + 1)
      tierNodes.forEach((node, rowIdx) => {
        positions[node.id] = {
          x: colWidth * (colIdx + 1),
          y: rowHeight * (rowIdx + 1),
        }
      })
    })

    return positions
  }, [nodes])

  if (activeCount === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-slate-600">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="opacity-30">
          <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
          <circle cx="36" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
          <circle cx="24" cy="36" r="4" stroke="currentColor" strokeWidth="2" />
          <line x1="15" y1="14" x2="21" y2="33" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="33" y1="14" x2="27" y2="33" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
          <line x1="16" y1="12" x2="32" y2="12" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 3" />
        </svg>
        <p className="text-xs">目前沒有進行中的工作流程</p>
        <p className="text-[10px] text-slate-700">執行 /diagnose 或 /ai:train 來啟動流程</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col gap-2">
      {title && (
        <h4 className="text-xs font-semibold text-slate-400">🔀 {title || '工作流程'}</h4>
      )}

      {/* DAG SVG canvas */}
      <div className="flex-1 min-h-[200px] relative">
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid meet"
          className="absolute inset-0"
        >
          {/* Defs */}
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#475569" />
            </marker>
            <marker id="arrowhead-active" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
              <polygon points="0 0, 8 3, 0 6" fill="#10b981" />
            </marker>
          </defs>

          {/* Edges */}
          {edges.map((edge, i) => {
            const from = layout[edge.from]
            const to = layout[edge.to]
            if (!from || !to) return null

            const isActive = nodes.find((n) => n.id === edge.to)?.status === 'working'

            return (
              <g key={`edge-${i}`}>
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={isActive ? '#10b981' : '#334155'}
                  strokeWidth={isActive ? 0.4 : 0.2}
                  strokeDasharray={isActive ? '' : '1 1'}
                  markerEnd={isActive ? 'url(#arrowhead-active)' : 'url(#arrowhead)'}
                  opacity={isActive ? 0.8 : 0.5}
                />
                {edge.label && (
                  <text
                    x={(from.x + to.x) / 2}
                    y={(from.y + to.y) / 2 - 1.5}
                    textAnchor="middle"
                    fontSize="2.5"
                    fill="#64748b"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const pos = layout[node.id]
            if (!pos) return null

            const colors = STATUS_COLORS[node.status] || STATUS_COLORS.idle
            const tierColor = TIER_COLORS[node.tier] || '#94a3b8'

            return (
              <g key={node.id}>
                {/* Node circle */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={4}
                  fill={colors.bg}
                  stroke={colors.border}
                  strokeWidth={0.4}
                  style={{ filter: colors.glow !== 'none' ? `drop-shadow(${colors.glow})` : undefined }}
                />

                {/* Tier indicator dot */}
                <circle cx={pos.x + 3.5} cy={pos.y - 3.5} r={1} fill={tierColor} />

                {/* Progress ring */}
                {node.progress != null && node.progress > 0 && node.progress < 100 && (
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={4.8}
                    fill="none"
                    stroke={colors.border}
                    strokeWidth={0.3}
                    strokeDasharray={`${(node.progress / 100) * 30.16} 30.16`}
                    strokeDashoffset={7.54}
                    strokeLinecap="round"
                  />
                )}

                {/* Name label */}
                <text
                  x={pos.x}
                  y={pos.y + 7}
                  textAnchor="middle"
                  fontSize="2.5"
                  fill={colors.text}
                  fontWeight={node.status === 'working' ? 'bold' : 'normal'}
                >
                  {node.label}
                </text>

                {/* Task label (if working) */}
                {node.task && node.status === 'working' && (
                  <text
                    x={pos.x}
                    y={pos.y + 10}
                    textAnchor="middle"
                    fontSize="1.8"
                    fill="#64748b"
                  >
                    {node.task.length > 20 ? node.task.slice(0, 18) + '…' : node.task}
                  </text>
                )}

                {/* Status icon */}
                <text
                  x={pos.x}
                  y={pos.y + 1}
                  textAnchor="middle"
                  fontSize="3"
                  dominantBaseline="middle"
                >
                  {node.status === 'working' ? '⚡' :
                   node.status === 'completed' ? '✅' :
                   node.status === 'waiting' ? '⏳' :
                   node.status === 'error' ? '❌' : '💤'}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-3 text-[9px] text-slate-500 px-2">
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-emerald-500" /> 執行中</span>
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-amber-500" /> 等待中</span>
        <span className="flex items-center gap-1"><span className="inline-block h-2 w-2 rounded-full bg-indigo-500" /> 完成</span>
        <span className="ml-auto text-slate-600">{activeCount} 個代理參與中</span>
      </div>
    </div>
  )
}
