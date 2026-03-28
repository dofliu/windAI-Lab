/**
 * ModernCompactView — 現代風格收合側邊欄。
 *
 * 視覺特徵：
 * - 圓形 avatar 直列排列
 * - 狀態用光暈環表示
 * - 極簡無文字，hover 才顯示資訊
 */

import { useState } from 'react'
import { type CompactViewProps } from '../types'
import { useTheme, getTierColor, getStatusColor } from '../../themes'
import { type AgentTier } from '../../types/agent'

const TIER_ORDER: AgentTier[] = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']

export default function ModernCompactView({
  agents,
  selectedAgent,
  onSelectAgent,
  collapsed,
}: CompactViewProps) {
  const { theme } = useTheme()
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  if (collapsed) {
    // 超窄模式：只顯示狀態指示點
    const working = agents.filter((a) => a.status === 'working' || a.status === 'waiting')
    return (
      <div className="flex flex-col items-center gap-1 py-2">
        {/* 工作中數量 */}
        <div
          className="flex h-6 w-6 items-center justify-center rounded-full text-[9px] font-bold"
          style={{
            backgroundColor: theme.statuses.working.bg,
            color: theme.statuses.working.dot,
          }}
        >
          {working.length}
        </div>
        <div className="w-4 border-t my-1" style={{ borderColor: theme.global.border }} />
        {/* 各 tier 指示 */}
        {TIER_ORDER.map((tier) => {
          const tierAgents = agents.filter((a) => a.tier === tier)
          const tierWorking = tierAgents.filter((a) => a.status === 'working').length
          const tierColor = getTierColor(theme, tier)
          return (
            <div
              key={tier}
              className="relative flex h-5 w-5 items-center justify-center rounded-full"
              style={{
                backgroundColor: tierColor.bg,
                border: `1.5px solid ${tierWorking > 0 ? tierColor.primary : theme.global.border}`,
              }}
              title={`${tier}: ${tierAgents.length} 人 / ${tierWorking} 工作中`}
            >
              <span className="text-[7px] font-bold" style={{ color: tierColor.primary }}>
                {tierAgents.length}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  // 展開的列表模式
  const grouped = TIER_ORDER.map((tier) => ({
    tier,
    agents: agents.filter((a) => a.tier === tier),
    color: getTierColor(theme, tier),
  }))

  return (
    <div className="h-full overflow-y-auto py-2 px-2">
      {grouped.map(({ tier, agents: tierAgents, color }) => (
        <div key={tier} className="mb-3">
          {/* Tier 標題 */}
          <div className="flex items-center gap-1.5 px-1 mb-1.5">
            <div
              className="h-1 w-1 rounded-full"
              style={{ backgroundColor: color.primary }}
            />
            <span className="text-[9px] font-medium uppercase tracking-wider" style={{ color: color.primary }}>
              {tier}
            </span>
          </div>

          {/* Agent 列表 */}
          {tierAgents.map((agent) => {
            const statusColor = getStatusColor(theme, agent.status)
            const isSelected = selectedAgent?.id === agent.id
            const isHovered = hoveredId === agent.id

            return (
              <button
                key={agent.id}
                onClick={() => onSelectAgent(agent)}
                onMouseEnter={() => setHoveredId(agent.id)}
                onMouseLeave={() => setHoveredId(null)}
                className="w-full flex items-center gap-2 rounded-lg px-2 py-1.5 transition-all duration-200"
                style={{
                  backgroundColor: isSelected
                    ? color.primary + '15'
                    : isHovered
                      ? theme.global.border + '30'
                      : 'transparent',
                  borderLeft: isSelected ? `2px solid ${color.primary}` : '2px solid transparent',
                }}
              >
                {/* Mini avatar */}
                <div
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[9px] font-semibold"
                  style={{
                    backgroundColor: color.bg,
                    color: color.primary,
                    boxShadow: agent.status === 'working' ? `0 0 6px ${statusColor.dot}40` : 'none',
                  }}
                >
                  {agent.displayName.charAt(0)}
                </div>

                {/* Name + status */}
                <div className="flex-1 min-w-0 text-left">
                  <div className="text-[10px] truncate" style={{ color: theme.global.textPrimary }}>
                    {agent.displayName}
                  </div>
                  {agent.currentTask && (
                    <div className="text-[8px] truncate" style={{ color: theme.global.textMuted }}>
                      {agent.currentTask}
                    </div>
                  )}
                </div>

                {/* Status dot */}
                <div
                  className="h-1.5 w-1.5 shrink-0 rounded-full"
                  style={{ backgroundColor: statusColor.dot }}
                />
              </button>
            )
          })}
        </div>
      ))}
    </div>
  )
}
