/**
 * MinimalOfficeView — 極簡白板風格辦公室視圖。
 *
 * 視覺特徵：
 * - 手繪虛線框表示房間
 * - 文字為主，幾乎無裝飾
 * - 代理用小圓點 + 名字呈現（像白板上的便利貼）
 * - 高對比、大留白
 * - 類似 Excalidraw / 手寫筆記的感覺
 */

import { useMemo } from 'react'
import { type OfficeViewProps } from '../types'
import { useTheme, getTierColor, getStatusColor, getRoomColor } from '../../themes'
import { type Agent, type AgentTier } from '../../types/agent'

const TIER_ORDER: AgentTier[] = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']
const TIER_LABELS: Record<string, string> = {
  leadership: '指揮',
  data: '資料',
  'ai-ml': '模型',
  domain: '領域',
  engineering: '工程',
  research: '研究',
}

function StickyNote({
  agent,
  isSelected,
  onClick,
  speechText,
}: {
  agent: Agent
  isSelected: boolean
  onClick: () => void
  speechText?: string
}) {
  const { theme } = useTheme()
  const tierColor = getTierColor(theme, agent.tier)
  const statusColor = getStatusColor(theme, agent.status)
  const isActive = agent.status === 'working' || agent.status === 'waiting'

  return (
    <button
      onClick={onClick}
      className="group relative text-left transition-all duration-200"
      style={{
        padding: '6px 10px',
        borderRadius: '2px',
        backgroundColor: isSelected ? tierColor.bgLight : 'transparent',
        borderLeft: `3px solid ${isActive ? statusColor.dot : isSelected ? tierColor.primary : 'transparent'}`,
        transform: isSelected ? 'rotate(-0.5deg)' : 'none',
      }}
    >
      <div className="flex items-center gap-2">
        {/* 手繪風格圓點 */}
        <div
          className="h-2 w-2 rounded-full shrink-0"
          style={{
            backgroundColor: statusColor.dot,
            boxShadow: isActive ? `0 0 4px ${statusColor.dot}` : 'none',
          }}
        />
        <span
          className="text-[11px]"
          style={{
            color: isSelected ? tierColor.primary : theme.global.textPrimary,
            fontWeight: isSelected ? 600 : 400,
          }}
        >
          {agent.displayName}
        </span>
      </div>

      {/* 任務（像手寫筆記） */}
      {agent.currentTask && (
        <div
          className="ml-4 mt-0.5 text-[9px] italic"
          style={{ color: theme.global.textMuted }}
        >
          → {agent.currentTask}
        </div>
      )}

      {/* 對話 */}
      {speechText && (
        <div
          className="ml-4 mt-1 text-[9px] rounded px-1.5 py-0.5"
          style={{
            backgroundColor: theme.global.border + '40',
            color: theme.global.textSecondary,
          }}
        >
          &ldquo;{speechText}&rdquo;
        </div>
      )}

      {/* 進度 */}
      {agent.progress != null && agent.progress > 0 && (
        <div className="ml-4 mt-1 flex items-center gap-1.5">
          <div
            className="h-[3px] w-16 rounded-full overflow-hidden"
            style={{ backgroundColor: theme.global.border }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${agent.progress}%`,
                backgroundColor: statusColor.dot,
              }}
            />
          </div>
          <span className="text-[8px]" style={{ color: theme.global.textMuted }}>
            {agent.progress}%
          </span>
        </div>
      )}
    </button>
  )
}

export default function MinimalOfficeView({
  rooms,
  selectedAgent,
  onSelectAgent,
  speechBubbles = [],
  isWarRoomActive,
}: OfficeViewProps) {
  const { theme } = useTheme()

  const bubbleMap = useMemo(() => {
    const m = new Map<string, string>()
    speechBubbles.forEach((b) => m.set(b.agentId, b.text))
    return m
  }, [speechBubbles])

  const allAgents = useMemo(() => rooms.flatMap((r) => r.agents), [rooms])
  const workingAgents = useMemo(
    () => allAgents.filter((a) => a.status === 'working' || a.status === 'waiting'),
    [allAgents],
  )

  const tierGroups = useMemo(() => {
    return TIER_ORDER.map((tier) => ({
      tier,
      label: TIER_LABELS[tier],
      agents: rooms.find((r) => r.tier === tier)?.agents ?? [],
    }))
  }, [rooms])

  return (
    <div className="h-full overflow-y-auto p-4" style={{ fontFamily: 'system-ui, sans-serif' }}>
      {/* 標題 */}
      <div className="mb-4">
        <h2 className="text-sm font-light tracking-widest uppercase" style={{ color: theme.global.textMuted }}>
          Office
        </h2>
        <div className="mt-1 border-b" style={{ borderColor: theme.global.border, borderStyle: 'dashed' }} />
      </div>

      {/* 活躍區域 */}
      {(isWarRoomActive || workingAgents.length > 0) && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <div
              className="h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: theme.statuses.working.dot }}
            />
            <span className="text-[10px] uppercase tracking-wider font-medium" style={{ color: theme.global.textSecondary }}>
              Active ({workingAgents.length})
            </span>
          </div>
          <div
            className="rounded-sm pl-3 py-2"
            style={{
              borderLeft: `2px solid ${theme.global.accent}`,
              backgroundColor: theme.global.accent + '06',
            }}
          >
            {workingAgents.map((agent) => (
              <StickyNote
                key={agent.id}
                agent={agent}
                isSelected={selectedAgent?.id === agent.id}
                onClick={() => onSelectAgent(agent)}
                speechText={bubbleMap.get(agent.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* 各部門 — 手繪虛線框 */}
      <div className="space-y-3">
        {tierGroups.map(({ tier, label, agents }) => {
          const roomColor = getRoomColor(theme, tier)

          return (
            <div
              key={tier}
              className="rounded-sm p-3"
              style={{
                border: `1px dashed ${roomColor.border}`,
                backgroundColor: roomColor.floor,
              }}
            >
              {/* 部門標題 */}
              <div className="flex items-center justify-between mb-2">
                <span
                  className="text-[10px] font-medium tracking-wide"
                  style={{ color: roomColor.label }}
                >
                  {label}
                </span>
                <span
                  className="text-[8px] font-mono"
                  style={{ color: theme.global.textMuted }}
                >
                  {agents.filter((a) => a.status === 'working').length}/{agents.length}
                </span>
              </div>

              {/* 代理列表 */}
              <div className="flex flex-col">
                {agents.map((agent) => (
                  <StickyNote
                    key={agent.id}
                    agent={agent}
                    isSelected={selectedAgent?.id === agent.id}
                    onClick={() => onSelectAgent(agent)}
                    speechText={bubbleMap.get(agent.id)}
                  />
                ))}
                {agents.length === 0 && (
                  <span className="text-[9px] italic" style={{ color: theme.global.textMuted }}>
                    (empty)
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
