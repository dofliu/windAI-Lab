/**
 * MissionView — 戰情中心 / 任務進行畫面。
 *
 * 當有任務執行時自動切換至此畫面，顯示：
 * - 左側：參與任務的代理清單 + 各自進度 + 即時訊息流
 * - 右側：分析結果面板（圖表、報告清單）
 *
 * 任務完成後自動切回辦公室畫面。
 */

import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { useTheme, getStatusColor, getTierColor } from '../themes'
import type { Agent, WorkLog } from '../types/agent'
import AvatarSVG from './AvatarSVG'

interface MissionViewProps {
  /** 所有代理（會自動過濾出任務中的） */
  agents: Agent[]
  /** 工作日誌 */
  workLogs: WorkLog[]
  /** 任務名稱 */
  missionTitle?: string
  /** 點選代理回呼 */
  onAgentClick?: (agent: Agent) => void
}

export default function MissionView({
  agents,
  workLogs,
  missionTitle,
  onAgentClick,
}: MissionViewProps) {
  const { theme } = useTheme()

  // 篩選出正在參與任務的代理（非 idle 且非 offline）
  const activeAgents = useMemo(
    () => agents.filter((a) => a.status !== 'idle'),
    [agents],
  )

  // 計算整體進度
  const overallProgress = useMemo(() => {
    if (activeAgents.length === 0) return 0
    const total = activeAgents.reduce((sum, a) => sum + (a.progress ?? 0), 0)
    return Math.round(total / activeAgents.length)
  }, [activeAgents])

  // 最近的工作日誌（最多 50 筆）
  const recentLogs = useMemo(() => workLogs.slice(-50).reverse(), [workLogs])

  // 代理進度長條圖資料
  const agentProgressData = useMemo(
    () =>
      activeAgents.map((a) => ({
        name: a.displayName.length > 6 ? a.displayName.slice(0, 6) + '…' : a.displayName,
        progress: a.progress ?? 0,
        color: getStatusColor(theme, a.status).dot,
      })),
    [activeAgents, theme],
  )

  // 狀態分佈圓餅圖資料
  const statusDistData = useMemo(() => {
    const counts: Record<string, number> = {}
    agents.forEach((a) => {
      counts[a.status] = (counts[a.status] ?? 0) + 1
    })
    const labels: Record<string, string> = {
      idle: '待命',
      working: '工作中',
      waiting: '等待',
      completed: '完成',
      error: '錯誤',
    }
    return Object.entries(counts)
      .filter(([, v]) => v > 0)
      .map(([status, value]) => ({
        name: labels[status] ?? status,
        value,
        color: getStatusColor(theme, status).dot,
      }))
  }, [agents, theme])

  // 任務標題
  const title = missionTitle || '任務進行中'

  return (
    <div className="flex h-full gap-0" style={{ color: theme.global.textPrimary }}>
      {/* ── 左側：代理面板 + 訊息流 ── */}
      <div
        className="flex flex-col border-r"
        style={{
          width: '380px',
          minWidth: '320px',
          borderColor: theme.global.border,
          backgroundColor: theme.global.panelBg,
        }}
      >
        {/* 任務標題 */}
        <div
          className="flex items-center gap-3 px-4 py-3 border-b"
          style={{ borderColor: theme.global.border }}
        >
          <div
            className="w-3 h-3 rounded-full animate-pulse-slow"
            style={{ backgroundColor: theme.statuses.working.dot }}
          />
          <div>
            <div className="text-sm font-bold">{title}</div>
            <div className="text-xs" style={{ color: theme.global.textSecondary }}>
              {activeAgents.length} 位代理參與
            </div>
          </div>
        </div>

        {/* 整體進度條 */}
        <div className="px-4 py-2">
          <div className="flex justify-between text-xs mb-1" style={{ color: theme.global.textSecondary }}>
            <span>整體進度</span>
            <span>{overallProgress}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: theme.global.border }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${overallProgress}%`,
                backgroundColor: theme.global.accent,
              }}
            />
          </div>
        </div>

        {/* 參與代理清單 */}
        <div className="flex-1 overflow-y-auto px-2 py-1">
          {activeAgents.map((agent) => (
            <AgentMissionCard
              key={agent.id}
              agent={agent}
              theme={theme}
              onClick={() => onAgentClick?.(agent)}
            />
          ))}
          {activeAgents.length === 0 && (
            <div
              className="text-center py-8 text-sm"
              style={{ color: theme.global.textMuted }}
            >
              目前沒有進行中的任務
            </div>
          )}
        </div>

        {/* 訊息流 */}
        <div
          className="border-t"
          style={{
            borderColor: theme.global.border,
            height: '35%',
            minHeight: '150px',
          }}
        >
          <div
            className="px-4 py-2 text-xs font-semibold border-b"
            style={{
              color: theme.global.textSecondary,
              borderColor: theme.global.border,
            }}
          >
            即時訊息
          </div>
          <div className="overflow-y-auto h-[calc(100%-32px)] px-3 py-1">
            {recentLogs.map((log) => (
              <LogEntry key={log.id} log={log} theme={theme} />
            ))}
          </div>
        </div>
      </div>

      {/* ── 右側：分析結果面板 ── */}
      <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: theme.global.pageBg }}>
        <div
          className="px-6 py-3 border-b flex items-center justify-between"
          style={{ borderColor: theme.global.border }}
        >
          <h2 className="text-sm font-bold" style={{ color: theme.global.textPrimary }}>
            分析儀表板
          </h2>
          <span className="text-xs" style={{ color: theme.global.textMuted }}>
            即時更新
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {/* 數據卡片 */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <MetricCard label="參與代理" value={`${activeAgents.length}`} theme={theme} />
            <MetricCard label="整體進度" value={`${overallProgress}%`} theme={theme} />
            <MetricCard label="日誌筆數" value={`${workLogs.length}`} theme={theme} />
          </div>

          {/* 圖表區域 */}
          {activeAgents.length > 0 && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              {/* 代理進度長條圖 */}
              <div
                className="rounded-xl border p-4"
                style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
              >
                <h3 className="text-xs font-semibold mb-3" style={{ color: theme.global.textSecondary }}>
                  代理進度
                </h3>
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={agentProgressData} layout="vertical">
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
                    <YAxis type="category" dataKey="name" width={70} tick={{ fontSize: 10, fill: theme.global.textSecondary }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: theme.global.panelBg,
                        border: `1px solid ${theme.global.border}`,
                        borderRadius: 8,
                        fontSize: 11,
                        color: theme.global.textPrimary,
                      }}
                      formatter={(value) => [`${value}%`, '進度']}
                    />
                    <Bar dataKey="progress" radius={[0, 4, 4, 0]}>
                      {agentProgressData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* 狀態分佈圓餅圖 */}
              <div
                className="rounded-xl border p-4"
                style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
              >
                <h3 className="text-xs font-semibold mb-3" style={{ color: theme.global.textSecondary }}>
                  代理狀態分佈
                </h3>
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={statusDistData}
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={70}
                      dataKey="value"
                      stroke="none"
                    >
                      {statusDistData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: theme.global.panelBg,
                        border: `1px solid ${theme.global.border}`,
                        borderRadius: 8,
                        fontSize: 11,
                        color: theme.global.textPrimary,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                {/* 圓餅圖圖例 */}
                <div className="flex justify-center gap-3 mt-1">
                  {statusDistData.map((d) => (
                    <span key={d.name} className="flex items-center gap-1 text-[10px]" style={{ color: theme.global.textSecondary }}>
                      <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: d.color }} />
                      {d.name} {d.value}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 結果/報告清單 */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold" style={{ color: theme.global.textSecondary }}>
              即時結果
            </h3>
            {recentLogs
              .filter((l) => l.type === 'success' || l.type === 'warning')
              .slice(0, 8)
              .map((log) => (
                <ResultCard key={log.id} log={log} theme={theme} />
              ))}
          </div>

          {activeAgents.length === 0 && (
            <div
              className="flex flex-col items-center justify-center h-64 rounded-xl border border-dashed"
              style={{ borderColor: theme.global.border, color: theme.global.textMuted }}
            >
              <div className="text-4xl mb-3 opacity-30">&#128202;</div>
              <div className="text-sm">任務啟動後將在此顯示分析結果</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── 子元件 ──────────────────────────────────────────────────

interface AgentMissionCardProps {
  agent: Agent
  theme: import('../themes').WindAITheme
  onClick?: () => void
}

function AgentMissionCard({ agent, theme, onClick }: AgentMissionCardProps) {
  const statusColor = getStatusColor(theme, agent.status)
  const tierColor = getTierColor(theme, agent.tier)

  return (
    <div
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 cursor-pointer transition-colors hover:opacity-90"
      style={{ backgroundColor: `${statusColor.bg}40` }}
      onClick={onClick}
    >
      {/* 頭像 */}
      <div className="relative flex-shrink-0">
        <AvatarSVG agentId={agent.id} tier={agent.tier} displayName={agent.displayName} size={36} />
        <div
          className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2"
          style={{
            backgroundColor: statusColor.dot,
            borderColor: theme.global.panelBg,
          }}
        />
      </div>

      {/* 資訊 */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{agent.displayName}</span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{ backgroundColor: tierColor.bg, color: tierColor.primary }}
          >
            {agent.tier}
          </span>
        </div>
        {agent.currentTask && (
          <div
            className="text-xs truncate mt-0.5"
            style={{ color: theme.global.textSecondary }}
          >
            {agent.currentTask}
          </div>
        )}
        {/* 個人進度條 */}
        {agent.status === 'working' && (
          <div className="mt-1.5">
            <div
              className="h-1.5 rounded-full overflow-hidden"
              style={{ backgroundColor: theme.global.border }}
            >
              <div
                className="h-full rounded-full transition-all duration-300"
                style={{
                  width: `${agent.progress ?? 0}%`,
                  backgroundColor: statusColor.dot,
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 進度數字 */}
      {agent.status === 'working' && (
        <span className="text-xs font-mono" style={{ color: statusColor.text }}>
          {agent.progress ?? 0}%
        </span>
      )}
    </div>
  )
}

interface LogEntryProps {
  log: WorkLog
  theme: import('../themes').WindAITheme
}

function LogEntry({ log, theme }: LogEntryProps) {
  const typeColors: Record<string, string> = {
    info: theme.global.textSecondary,
    success: theme.statuses.working.dot,
    warning: theme.statuses.waiting.dot,
    error: theme.statuses.error.dot,
  }
  const color = typeColors[log.type ?? 'info'] ?? theme.global.textSecondary

  return (
    <div className="flex gap-2 py-1 text-xs">
      <span className="flex-shrink-0 font-mono" style={{ color: theme.global.textMuted }}>
        {new Date(log.timestamp).toLocaleTimeString('zh-TW', { hour12: false })}
      </span>
      <span className="font-medium flex-shrink-0" style={{ color }}>
        {log.agentName}
      </span>
      <span className="truncate" style={{ color: theme.global.textSecondary }}>
        {log.message}
      </span>
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string
  theme: import('../themes').WindAITheme
}

function MetricCard({ label, value, theme }: MetricCardProps) {
  return (
    <div
      className="rounded-xl px-4 py-3 border"
      style={{
        backgroundColor: theme.global.panelBg,
        borderColor: theme.global.border,
      }}
    >
      <div className="text-xs mb-1" style={{ color: theme.global.textSecondary }}>
        {label}
      </div>
      <div className="text-xl font-bold" style={{ color: theme.global.accent }}>
        {value}
      </div>
    </div>
  )
}

interface ResultCardProps {
  log: WorkLog
  theme: import('../themes').WindAITheme
}

function ResultCard({ log, theme }: ResultCardProps) {
  return (
    <div
      className="rounded-xl px-4 py-3 border"
      style={{
        backgroundColor: theme.global.panelBg,
        borderColor: theme.global.border,
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: theme.statuses.working.dot }}
        />
        <span className="text-sm font-medium">{log.agentName}</span>
        <span className="text-xs ml-auto" style={{ color: theme.global.textMuted }}>
          {new Date(log.timestamp).toLocaleTimeString('zh-TW', { hour12: false })}
        </span>
      </div>
      <div className="text-sm" style={{ color: theme.global.textSecondary }}>
        {log.message}
      </div>
    </div>
  )
}
