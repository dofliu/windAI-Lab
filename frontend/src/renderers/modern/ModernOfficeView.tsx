/**
 * ModernOfficeView — 現代企業風辦公室視圖。
 *
 * 視覺特徵：
 * - Glassmorphism 毛玻璃卡片
 * - 大圓角 + 柔和陰影
 * - 代理用圓形 avatar + 狀態環表示
 * - 房間以 grid 卡片呈現，非像素地圖
 * - 動態光暈效果取代像素走路動畫
 */

import { useState, useMemo } from 'react'
import { type OfficeViewProps } from '../types'
import { useTheme, getTierColor, getStatusColor, getRoomColor } from '../../themes'
import { type Agent, type AgentTier } from '../../types/agent'

const TIER_META: Record<string, { label: string; icon: string }> = {
  leadership:  { label: '指揮中心', icon: '⚡' },
  data:        { label: '資料工程', icon: '◈' },
  'ai-ml':     { label: '模型實驗', icon: '◉' },
  domain:      { label: '領域知識', icon: '◎' },
  engineering: { label: '軟體工程', icon: '⬡' },
  research:    { label: '研究室',   icon: '◆' },
}

function AgentOrb({
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
      className="group relative flex flex-col items-center gap-1 transition-all duration-300"
      style={{ outline: 'none' }}
    >
      {/* 對話氣泡 */}
      {speechText && (
        <div
          className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full px-2 py-0.5 text-[9px] shadow-lg"
          style={{
            backgroundColor: theme.global.panelBg + 'ee',
            color: theme.global.textSecondary,
            border: `1px solid ${theme.global.border}`,
          }}
        >
          {speechText}
        </div>
      )}

      {/* Avatar 圓環 */}
      <div
        className="relative flex h-10 w-10 items-center justify-center rounded-full transition-all duration-300"
        style={{
          background: isSelected
            ? `linear-gradient(135deg, ${tierColor.primary}40, ${tierColor.primary}20)`
            : theme.global.panelBg,
          border: `2px solid ${isSelected ? tierColor.primary : theme.global.border}`,
          boxShadow: isActive
            ? `0 0 12px ${statusColor.dot}40, 0 0 24px ${statusColor.dot}20`
            : isSelected
              ? `0 0 8px ${tierColor.primary}30`
              : 'none',
        }}
      >
        {/* 狀態脈衝環 */}
        {isActive && (
          <div
            className="absolute inset-0 rounded-full"
            style={{
              border: `2px solid ${statusColor.dot}`,
              animation: 'modern-pulse 2s ease-in-out infinite',
            }}
          />
        )}

        {/* 首字母 */}
        <span
          className="text-xs font-semibold"
          style={{ color: tierColor.primary }}
        >
          {agent.displayName.charAt(0)}
        </span>

        {/* 狀態指示點 */}
        <div
          className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2"
          style={{
            backgroundColor: statusColor.dot,
            borderColor: theme.global.panelBg,
          }}
        />
      </div>

      {/* 名稱 */}
      <span
        className="text-[8px] leading-tight opacity-70 group-hover:opacity-100 transition-opacity max-w-[52px] truncate"
        style={{ color: theme.global.textSecondary }}
      >
        {agent.displayName}
      </span>

      {/* 進度條 */}
      {agent.progress != null && agent.progress > 0 && (
        <div
          className="h-0.5 w-8 rounded-full overflow-hidden"
          style={{ backgroundColor: theme.global.border }}
        >
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${agent.progress}%`,
              backgroundColor: statusColor.dot,
            }}
          />
        </div>
      )}
    </button>
  )
}

export default function ModernOfficeView({
  rooms,
  selectedAgent,
  onSelectAgent,
  speechBubbles = [],
  isWarRoomActive,
}: OfficeViewProps) {
  const { theme } = useTheme()
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null)

  const bubbleMap = useMemo(() => {
    const m = new Map<string, string>()
    speechBubbles.forEach((b) => m.set(b.agentId, b.text))
    return m
  }, [speechBubbles])

  const allAgents = useMemo(() => rooms.flatMap((r) => r.agents), [rooms])

  // 正在工作的代理（顯示在頂部「戰情室」區域）
  const workingAgents = useMemo(
    () => allAgents.filter((a) => a.status === 'working' || a.status === 'waiting'),
    [allAgents],
  )

  const tierRooms = useMemo(() => {
    const order: AgentTier[] = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']
    return order.map((tier) => {
      const room = rooms.find((r) => r.tier === tier)
      const agents = room?.agents ?? []
      return { tier, agents, meta: TIER_META[tier] }
    })
  }, [rooms])

  return (
    <div className="h-full flex flex-col gap-3 p-3 overflow-y-auto">
      {/* ── 戰情室（活躍代理） ── */}
      {(isWarRoomActive || workingAgents.length > 0) && (
        <div
          className="rounded-2xl p-3 backdrop-blur-md"
          style={{
            background: `linear-gradient(135deg, ${theme.global.accent}08, ${theme.global.accent}03)`,
            border: `1px solid ${theme.global.accent}25`,
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <div
              className="h-1.5 w-1.5 rounded-full"
              style={{
                backgroundColor: theme.statuses.working.dot,
                animation: 'modern-pulse 1.5s ease-in-out infinite',
              }}
            />
            <span className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>
              活躍中 · {workingAgents.length} 位
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            {workingAgents.map((agent) => (
              <AgentOrb
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

      {/* ── 部門 Grid ── */}
      <div className="grid grid-cols-2 gap-2 flex-1">
        {tierRooms.map(({ tier, agents, meta }) => {
          const roomColor = getRoomColor(theme, tier)
          const isHovered = hoveredRoom === tier

          return (
            <div
              key={tier}
              className="rounded-2xl p-3 transition-all duration-300 backdrop-blur-sm"
              style={{
                background: isHovered
                  ? `linear-gradient(145deg, ${roomColor.floor}, ${theme.global.panelBg})`
                  : theme.global.panelBg + '80',
                border: `1px solid ${isHovered ? roomColor.border : theme.global.border}60`,
                boxShadow: isHovered ? `0 4px 20px ${roomColor.border}15` : 'none',
              }}
              onMouseEnter={() => setHoveredRoom(tier)}
              onMouseLeave={() => setHoveredRoom(null)}
            >
              {/* 房間標頭 */}
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-xs opacity-60">{meta.icon}</span>
                <span
                  className="text-[10px] font-semibold tracking-wide uppercase"
                  style={{ color: roomColor.label }}
                >
                  {meta.label}
                </span>
                <span
                  className="ml-auto text-[9px] rounded-full px-1.5 py-0.5"
                  style={{
                    backgroundColor: roomColor.floor,
                    color: roomColor.label,
                  }}
                >
                  {agents.length}
                </span>
              </div>

              {/* 代理們 */}
              <div className="flex flex-wrap gap-2">
                {agents.map((agent) => (
                  <AgentOrb
                    key={agent.id}
                    agent={agent}
                    isSelected={selectedAgent?.id === agent.id}
                    onClick={() => onSelectAgent(agent)}
                    speechText={bubbleMap.get(agent.id)}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
