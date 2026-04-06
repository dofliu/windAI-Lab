/**
 * MissionAgentPanel — 戰情中心代理面板。
 *
 * 在任務進行中只顯示參與的代理，含即時進度、狀態、當前工作描述。
 * 與 WorkflowProgress 搭配使用，構成完整戰情中心。
 */

import { useMemo } from 'react'
import { useTheme, getTierColor, getStatusColor } from '../themes'
import type { Agent, WorkLog } from '../types/agent'

interface MissionAgentPanelProps {
  agents: Agent[]
  workLogs: WorkLog[]
  isCompleted: boolean
}

export default function MissionAgentPanel({ agents, workLogs, isCompleted }: MissionAgentPanelProps) {
  const { theme } = useTheme()

  // 從日誌中找出參與的代理
  const participatingIds = useMemo(() => {
    const ids = new Set<string>()
    workLogs.forEach((l) => {
      if (l.agentId !== 'system') ids.add(l.agentId)
    })
    // 加入正在工作或等待中的代理
    agents.forEach((a) => {
      if (a.status === 'working' || a.status === 'waiting') ids.add(a.id)
    })
    return ids
  }, [agents, workLogs])

  const participatingAgents = useMemo(
    () => agents.filter((a) => participatingIds.has(a.id)),
    [agents, participatingIds],
  )

  // 每個代理的最新日誌
  const latestLogByAgent = useMemo(() => {
    const map = new Map<string, WorkLog>()
    workLogs.forEach((l) => {
      if (l.agentId !== 'system') map.set(l.agentId, l)
    })
    return map
  }, [workLogs])

  if (participatingAgents.length === 0) return null

  return (
    <div className="space-y-1">
      <div className="text-[10px] font-medium px-1 mb-1" style={{ color: theme.global.textSecondary }}>
        參與代理 ({participatingAgents.length})
      </div>
      {participatingAgents.map((agent) => {
        const tierColor = getTierColor(theme, agent.tier)
        const statusColor = getStatusColor(theme, agent.status)
        const latestLog = latestLogByAgent.get(agent.id)
        const progress = agent.progress ?? 0
        const isActive = agent.status === 'working' || agent.status === 'waiting'

        return (
          <div
            key={agent.id}
            className="rounded-lg border px-3 py-2 transition-all"
            style={{
              borderColor: isActive ? tierColor.primary + '60' : theme.global.border + '40',
              backgroundColor: isActive ? tierColor.primary + '08' : 'transparent',
            }}
          >
            {/* Agent header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    backgroundColor: statusColor.dot,
                    boxShadow: isActive ? `0 0 6px ${statusColor.dot}` : 'none',
                  }}
                />
                <span className="text-[11px] font-medium" style={{ color: theme.global.textPrimary }}>
                  {agent.displayName}
                </span>
                <span
                  className="text-[8px] rounded-full px-1.5 py-0.5"
                  style={{ backgroundColor: tierColor.bg, color: tierColor.primary }}
                >
                  {agent.tier}
                </span>
              </div>
              <span className="text-[9px]" style={{ color: statusColor.dot }}>
                {isCompleted
                  ? '已完成'
                  : agent.status === 'working'
                    ? `${progress}%`
                    : agent.status === 'waiting'
                      ? '等待中'
                      : '待命'}
              </span>
            </div>

            {/* Progress bar (only when active) */}
            {isActive && (
              <div
                className="mt-1.5 h-1 w-full rounded-full overflow-hidden"
                style={{ backgroundColor: theme.global.border + '60' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(progress, 100)}%`,
                    backgroundColor: statusColor.dot,
                  }}
                />
              </div>
            )}

            {/* Current task / latest log */}
            {(agent.currentTask || latestLog) && (
              <div
                className="mt-1 text-[9px] truncate"
                style={{ color: theme.global.textMuted }}
              >
                {agent.currentTask || latestLog?.message}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
