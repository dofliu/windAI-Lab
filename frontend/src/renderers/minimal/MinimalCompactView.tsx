/**
 * MinimalCompactView — 極簡風格收合側邊欄。
 *
 * 純文字為主，高密度資訊顯示。
 */

import { type CompactViewProps } from '../types'
import { useTheme, getTierColor, getStatusColor } from '../../themes'
import { type AgentTier } from '../../types/agent'

const TIER_ORDER: AgentTier[] = ['leadership', 'data', 'ai-ml', 'domain', 'engineering', 'research']

export default function MinimalCompactView({
  agents,
  selectedAgent,
  onSelectAgent,
  collapsed,
}: CompactViewProps) {
  const { theme } = useTheme()

  if (collapsed) {
    const working = agents.filter((a) => a.status === 'working' || a.status === 'waiting')
    return (
      <div className="flex flex-col items-center gap-2 py-3">
        <span className="text-[10px] font-mono" style={{ color: theme.global.textSecondary }}>
          {working.length}
        </span>
        <div className="w-3 border-t" style={{ borderColor: theme.global.border, borderStyle: 'dashed' }} />
        <span className="text-[8px]" style={{ color: theme.global.textMuted }}>
          /{agents.length}
        </span>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto py-2 px-3">
      {TIER_ORDER.map((tier) => {
        const tierAgents = agents.filter((a) => a.tier === tier)
        const tierColor = getTierColor(theme, tier)
        if (tierAgents.length === 0) return null

        return (
          <div key={tier} className="mb-3">
            <div
              className="text-[8px] uppercase tracking-widest mb-1 pb-0.5 border-b"
              style={{
                color: tierColor.primary,
                borderColor: theme.global.border,
                borderStyle: 'dashed',
              }}
            >
              {tier}
            </div>
            {tierAgents.map((agent) => {
              const statusColor = getStatusColor(theme, agent.status)
              const isSelected = selectedAgent?.id === agent.id

              return (
                <button
                  key={agent.id}
                  onClick={() => onSelectAgent(agent)}
                  className="w-full flex items-center gap-1.5 py-1 px-1 text-left transition-colors duration-150 rounded-sm"
                  style={{
                    backgroundColor: isSelected ? tierColor.primary + '10' : 'transparent',
                  }}
                >
                  <div
                    className="h-1.5 w-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: statusColor.dot }}
                  />
                  <span
                    className="text-[10px] truncate flex-1"
                    style={{
                      color: isSelected ? theme.global.textPrimary : theme.global.textSecondary,
                    }}
                  >
                    {agent.displayName}
                  </span>
                </button>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
