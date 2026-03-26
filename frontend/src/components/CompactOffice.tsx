import { useState, useMemo } from 'react'
import { Agent, AgentTier } from '../types/agent'
import { useTheme, getTierColor, getStatusColor } from '../themes'

/* ── Tier 設定 ── */

interface TierConfig {
  label: string
  icon: string
}

const TIERS: Record<AgentTier, TierConfig> = {
  leadership:  { label: '指揮', icon: '🏛️' },
  data:        { label: '資料', icon: '🗃️' },
  'ai-ml':     { label: '模型', icon: '🧠' },
  domain:      { label: '領域', icon: '🌬️' },
  engineering: { label: '工程', icon: '💻' },
  research:    { label: '研究', icon: '📖' },
}

const TIER_ORDER: AgentTier[] = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']

/* ── 代理簡稱對照表（取一個代表字） ── */
const SHORT_NAME: Record<string, string> = {
  'project-director':     '總',
  'research-lead':        '研',
  'project-manager':      '管',
  'tech-lead':            '技',
  'scada-processor':      'SC',
  'quality-checker':      '檢',
  'etl-engineer':         'ET',
  'data-validator':       '驗',
  'stream-processor':     '流',
  'storage-manager':      '存',
  'metadata-curator':     '元',
  'pipeline-monitor':     '監',
  'fault-diagnostician':  '診',
  'predictive-modeler':   '預',
  'rag-architect':        'RA',
  'model-trainer':        '訓',
  'experiment-tracker':   '驗',
  'model-evaluator':      '評',
  'anomaly-detector':     '異',
  'feature-engineer':     '特',
  'hyperparameter-tuner': '調',
  'inference-deployer':   '佈',
  'power-curve-expert':   '曲',
  'maintenance-planner':  '維',
  'wake-analyst':         '尾',
  'wind-resource-analyst':'風',
  'iec-specialist':       'IE',
  'regulatory-advisor':   '法',
  'backend-dev':          '後',
  'test-engineer':        '測',
  'devops-engineer':      'DV',
  'frontend-dev':         '前',
  'api-designer':         'AP',
  'database-admin':       'DB',
  'security-analyst':     '安',
  'infra-manager':        '架',
  'paper-writer':         '論',
  'literature-reviewer':  '文',
  'rag-curator':          '庫',
  'report-generator':     '報',
  'teaching-assistant':   '教',
  'data-storyteller':     '敘',
}

function getShortName(agent: Agent): string {
  return SHORT_NAME[agent.id] || agent.displayName.charAt(0)
}

/* ── Hash for deterministic appearance ── */
function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (s.charCodeAt(i) + ((h << 5) - h)) | 0
  return Math.abs(h)
}

/* ── Mini avatar (head + short name label) ── */
function MiniAvatar({ agent, size = 28, selected, onClick, showLabel = true }: {
  agent: Agent
  size?: number
  selected?: boolean
  onClick?: () => void
  showLabel?: boolean
}) {
  const { theme } = useTheme()
  const h = hash(agent.id)
  const tierColor = getTierColor(theme, agent.tier)
  const statusColor = getStatusColor(theme, agent.status)
  const shirt = tierColor.primary
  const skinColors = ['#f5c6a0', '#e8b896', '#d4a574', '#c49a6c', '#f0d5b8']
  const hairColors = ['#1a1a2e', '#3d2b1f', '#8b6914', '#5b2c6f', '#2c3e50']
  const skin = skinColors[h % skinColors.length]
  const hair = hairColors[h % hairColors.length]
  const shortName = getShortName(agent)

  const statusAnim = agent.status === 'working' || agent.status === 'waiting' ? 'animate-pulse' : ''

  return (
    <button
      onClick={onClick}
      title={`${agent.displayName} — ${agent.currentTask || agent.status}`}
      className={`group relative flex shrink-0 flex-col items-center gap-0.5 transition-all hover:scale-105 ${selected ? 'scale-105' : ''}`}
    >
      {/* Avatar ring */}
      <div
        className="rounded-full ring-2"
        style={{
          ['--tw-ring-color' as string]: statusColor.dot,
          ['--tw-ring-offset-color' as string]: selected ? theme.global.border : 'transparent',
        }}
      >
        <svg
          viewBox="0 0 16 14"
          width={size}
          height={size * 0.875}
          style={{ shapeRendering: 'crispEdges' }}
        >
          <rect x="4" y="0" width="8" height="3" fill={hair} />
          <rect x="3" y="1" width="1" height="4" fill={hair} />
          <rect x="12" y="1" width="1" height="4" fill={hair} />
          <rect x="4" y="3" width="8" height="6" fill={skin} />
          <rect x="5" y="5" width="2" height="2" fill="#1a1a2e" />
          <rect x="9" y="5" width="2" height="2" fill="#1a1a2e" />
          <rect x="5" y="5" width="1" height="1" fill="white" />
          <rect x="9" y="5" width="1" height="1" fill="white" />
          <rect x="6" y="7" width="4" height="1" fill={skin} opacity="0.6" />
          <rect x="4" y="9" width="8" height="3" fill={shirt} />
          <rect x="3" y="10" width="1" height="3" fill={shirt} />
          <rect x="12" y="10" width="1" height="3" fill={shirt} />
        </svg>
        {/* Status dot */}
        <span
          className={`absolute top-0 -right-0.5 h-2 w-2 rounded-full border ${statusAnim}`}
          style={{ backgroundColor: statusColor.dot, borderColor: theme.global.panelBg }}
        />
      </div>
      {/* Short name label */}
      {showLabel && (
        <span className="text-[8px] leading-none" style={{ color: statusColor.text }}>
          {shortName}
        </span>
      )}
    </button>
  )
}

/* ── Main CompactOffice ── */

interface CompactOfficeProps {
  agents: Agent[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
  collapsed?: boolean
}

export default function CompactOffice({
  agents,
  selectedAgent,
  onSelectAgent,
  collapsed = false,
}: CompactOfficeProps) {
  const { theme } = useTheme()
  const [expandedTier, setExpandedTier] = useState<AgentTier | null>(null)

  const grouped = useMemo(() => {
    const map: Record<AgentTier, Agent[]> = {} as any
    TIER_ORDER.forEach((t) => (map[t] = []))
    agents.forEach((a) => map[a.tier]?.push(a))
    return map
  }, [agents])

  const workingCount = agents.filter((a) => a.status === 'working').length
  const waitingCount = agents.filter((a) => a.status === 'waiting').length

  /* ── Collapsed: icon strip ── */
  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 px-1">
        {TIER_ORDER.map((tier) => {
          const cfg = TIERS[tier]
          const tierColor = getTierColor(theme, tier)
          const tierAgents = grouped[tier]
          const working = tierAgents.filter((a) => a.status !== 'idle').length
          return (
            <div key={tier} className="relative" title={`${cfg.label} (${tierAgents.length}人)`}>
              <span className="text-base">{cfg.icon}</span>
              {working > 0 && (
                <span
                  className="absolute -top-1 -right-2 flex h-3.5 w-3.5 items-center justify-center rounded-full text-[7px] font-bold text-white"
                  style={{ backgroundColor: tierColor.primary }}
                >
                  {working}
                </span>
              )}
            </div>
          )
        })}
        {/* Summary counts */}
        <div className="mt-2 flex flex-col items-center gap-1 border-t pt-2" style={{ borderColor: theme.global.border }}>
          <div className="flex items-center gap-1" title="工作中">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: theme.statuses.working.dot }} />
            <span className="text-[9px]" style={{ color: theme.global.textSecondary }}>{workingCount}</span>
          </div>
          {waitingCount > 0 && (
            <div className="flex items-center gap-1" title="等待確認">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: theme.statuses.waiting.dot }} />
              <span className="text-[9px]" style={{ color: theme.global.textSecondary }}>{waitingCount}</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  /* ── Expanded: grouped avatar grid ── */
  return (
    <div className="flex h-full flex-col overflow-y-auto px-3 py-3">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-bold" style={{ color: theme.global.textPrimary }}>
          🏢 研究室
          <span className="ml-1.5 text-[9px] font-normal" style={{ color: theme.global.textMuted }}>
            {agents.length}人
          </span>
        </h2>
        <div className="flex items-center gap-2 text-[9px]" style={{ color: theme.global.textMuted }}>
          <span className="flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: theme.statuses.working.dot }} />
            {workingCount}
          </span>
          {waitingCount > 0 && (
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: theme.statuses.waiting.dot }} />
              {waitingCount}
            </span>
          )}
        </div>
      </div>

      {/* Tier groups */}
      <div className="flex flex-col gap-2">
        {TIER_ORDER.map((tier) => {
          const cfg = TIERS[tier]
          const tierColor = getTierColor(theme, tier)
          const tierAgents = grouped[tier]
          const isExpanded = expandedTier === tier
          const tierWorking = tierAgents.filter((a) => a.status !== 'idle').length

          return (
            <div
              key={tier}
              className="rounded-lg border transition-colors"
              style={{
                borderColor: isExpanded ? tierColor.primary + '4d' : theme.global.border + '66',
                backgroundColor: isExpanded ? tierColor.primary + '0d' : theme.global.panelBg + '66',
              }}
            >
              {/* Tier header */}
              <button
                onClick={() => setExpandedTier(isExpanded ? null : tier)}
                className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left"
              >
                <span className="text-xs">{cfg.icon}</span>
                <span className="text-[10px] font-medium" style={{ color: theme.global.textPrimary }}>{cfg.label}</span>
                <span className="text-[9px]" style={{ color: theme.global.textMuted }}>{tierAgents.length}人</span>
                {tierWorking > 0 && (
                  <span className="ml-auto flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ backgroundColor: theme.statuses.working.dot }} />
                    <span className="text-[9px]" style={{ color: theme.statuses.working.text }}>{tierWorking}</span>
                  </span>
                )}
                <span className={`ml-auto text-[8px] transition-transform ${isExpanded ? 'rotate-90' : ''}`} style={{ color: theme.global.textMuted }}>
                  ▶
                </span>
              </button>

              {/* Avatar grid (always visible, compact) */}
              <div className="flex flex-wrap gap-1.5 px-2.5 pb-2">
                {tierAgents.map((agent) => (
                  <MiniAvatar
                    key={agent.id}
                    agent={agent}
                    size={isExpanded ? 32 : 24}
                    selected={selectedAgent?.id === agent.id}
                    onClick={() => onSelectAgent(agent)}
                  />
                ))}
              </div>

              {/* Expanded detail: agent names */}
              {isExpanded && (
                <div className="border-t px-2.5 py-2" style={{ borderColor: theme.global.border + '4d' }}>
                  {tierAgents.map((agent) => {
                    const sc = getStatusColor(theme, agent.status)
                    return (
                      <button
                        key={agent.id}
                        onClick={() => onSelectAgent(agent)}
                        className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left transition-colors hover:opacity-80"
                        style={{
                          backgroundColor: selectedAgent?.id === agent.id ? theme.global.border + '66' : 'transparent',
                        }}
                      >
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: sc.dot }} />
                        <span className="truncate text-[10px]" style={{ color: theme.global.textPrimary }}>{agent.displayName}</span>
                        {agent.status === 'working' && agent.currentTask && (
                          <span className="ml-auto truncate text-[8px] max-w-[80px]" style={{ color: sc.text + 'b3' }}>
                            {agent.currentTask}
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Selected agent quick info */}
      {selectedAgent && (
        <div
          className="mt-3 rounded-lg border px-3 py-2"
          style={{ borderColor: theme.global.accent + '4d', backgroundColor: theme.global.accent + '0d' }}
        >
          <div className="flex items-center gap-2">
            <MiniAvatar agent={selectedAgent} size={28} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[10px] font-medium" style={{ color: theme.global.textPrimary }}>{selectedAgent.displayName}</p>
              <p className="truncate text-[9px]" style={{ color: theme.global.textSecondary }}>{selectedAgent.name}</p>
            </div>
          </div>
          {selectedAgent.currentTask && (
            <p className="mt-1.5 text-[9px]" style={{ color: theme.global.textSecondary }}>
              📋 {selectedAgent.currentTask}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
