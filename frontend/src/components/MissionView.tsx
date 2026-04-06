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
  ScatterChart, Scatter, CartesianGrid,
  LineChart, Line, Legend,
} from 'recharts'
import { useTheme, getStatusColor, getTierColor } from '../themes'
import type { Agent, WorkLog } from '../types/agent'
import AvatarSVG from './AvatarSVG'

/** 後端推送的分析結果 */
interface AnalysisResultPayload {
  chart_type: string
  title: string
  data: Array<Record<string, number | string>>
  metadata?: Record<string, number | string>
}

interface MissionViewProps {
  /** 所有代理（會自動過濾出任務中的） */
  agents: Agent[]
  /** 工作日誌 */
  workLogs: WorkLog[]
  /** 後端推送的分析結果 */
  analysisResults?: AnalysisResultPayload[]
  /** 任務名稱 */
  missionTitle?: string
  /** 點選代理回呼 */
  onAgentClick?: (agent: Agent) => void
  /** 任務已完成（顯示結果查看模式） */
  isCompleted?: boolean
  /** 關閉戰情中心回到辦公室 */
  onClose?: () => void
}

export default function MissionView({
  agents,
  workLogs,
  analysisResults = [],
  missionTitle,
  onAgentClick,
  isCompleted = false,
  onClose,
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

  // 從工作日誌中提取數值指標
  const extractedMetrics = useMemo(() => {
    const metrics: Array<{ name: string; value: number; agent: string; timestamp: number }> = []
    const patterns = [
      { regex: /R[²2]\s*[=:]\s*([\d.]+)/i, name: 'R²' },
      { regex: /F1\s*[=:]\s*([\d.]+)/i, name: 'F1' },
      { regex: /MAE\s*[=:]\s*([\d.]+)/i, name: 'MAE' },
      { regex: /RMSE\s*[=:]\s*([\d.]+)/i, name: 'RMSE' },
      { regex: /健康分數\s*([\d.]+)/i, name: '健康分數' },
      { regex: /容量因數[：:]\s*([\d.]+)/i, name: '容量因數' },
      { regex: /可用率[：:]\s*([\d.]+)/i, name: '可用率' },
      { regex: /偏差[：:]\s*(-?[\d.]+)/i, name: '功率偏差%' },
      { regex: /異常點\s*([\d]+)\s*個/i, name: '異常點' },
    ]
    workLogs.forEach((log) => {
      patterns.forEach(({ regex, name }) => {
        const match = log.message.match(regex)
        if (match) {
          metrics.push({
            name,
            value: parseFloat(match[1]),
            agent: log.agentName,
            timestamp: log.timestamp.getTime(),
          })
        }
      })
    })
    return metrics
  }, [workLogs])

  // 任務標題
  const title = missionTitle || (isCompleted ? '任務已完成' : '任務進行中')

  // 完成模式下也顯示曾參與的代理（從日誌中推導）
  const displayAgents = useMemo(() => {
    if (activeAgents.length > 0) return activeAgents
    // 任務完成後所有代理回到 idle，從日誌推導曾參與的代理 ID
    const logAgentIds = new Set(workLogs.map((l) => l.agentId).filter((id) => id !== 'system'))
    return agents.filter((a) => logAgentIds.has(a.id))
  }, [activeAgents, agents, workLogs])

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
            className={`w-3 h-3 rounded-full ${isCompleted ? '' : 'animate-pulse-slow'}`}
            style={{ backgroundColor: isCompleted ? theme.statuses.completed.dot : theme.statuses.working.dot }}
          />
          <div className="flex-1">
            <div className="text-sm font-bold">{title}</div>
            <div className="text-xs" style={{ color: theme.global.textSecondary }}>
              {displayAgents.length} 位代理參與
            </div>
          </div>
          {isCompleted && onClose && (
            <button
              onClick={onClose}
              className="rounded-lg border px-3 py-1 text-xs font-medium transition-colors hover:brightness-125"
              style={{
                borderColor: theme.global.accent + '60',
                backgroundColor: theme.global.accent + '20',
                color: theme.global.accent,
              }}
            >
              返回辦公室
            </button>
          )}
        </div>

        {/* 完成提示橫幅 */}
        {isCompleted && (
          <div
            className="px-4 py-2 text-xs font-medium border-b"
            style={{
              borderColor: theme.global.border,
              backgroundColor: theme.statuses.completed.bg,
              color: theme.statuses.completed.dot,
            }}
          >
            任務已完成 — 以下為執行結果，點擊「返回辦公室」可關閉此畫面
          </div>
        )}

        {/* 整體進度條 */}
        <div className="px-4 py-2">
          <div className="flex justify-between text-xs mb-1" style={{ color: theme.global.textSecondary }}>
            <span>整體進度</span>
            <span>{isCompleted ? 100 : overallProgress}%</span>
          </div>
          <div className="h-2 rounded-full overflow-hidden" style={{ backgroundColor: theme.global.border }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${isCompleted ? 100 : overallProgress}%`,
                backgroundColor: isCompleted ? theme.statuses.completed.dot : theme.global.accent,
              }}
            />
          </div>
        </div>

        {/* 參與代理清單 */}
        <div className="flex-1 overflow-y-auto px-2 py-1">
          {displayAgents.map((agent) => (
            <AgentMissionCard
              key={agent.id}
              agent={agent}
              theme={theme}
              onClick={() => onAgentClick?.(agent)}
            />
          ))}
          {displayAgents.length === 0 && (
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
          className="px-4 py-2 border-b flex items-center justify-between"
          style={{ borderColor: theme.global.border }}
        >
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-bold" style={{ color: theme.global.textPrimary }}>
              分析儀表板
            </h2>
            {analysisResults.length > 0 && (
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{ backgroundColor: theme.global.accent + '20', color: theme.global.accent }}
              >
                {analysisResults.length} 項結果
              </span>
            )}
          </div>
          <div className="flex items-center gap-4 text-[10px]" style={{ color: theme.global.textMuted }}>
            <span>代理 {displayAgents.length}</span>
            <span>日誌 {workLogs.length}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {/* 任務進行中：顯示代理進度 */}
          {!isCompleted && displayAgents.length > 0 && (
            <div className="grid grid-cols-2 gap-3 mb-4">
              <ChartPanel title="代理進度" theme={theme}>
                <ResponsiveContainer width="100%" height={140}>
                  <BarChart data={agentProgressData} layout="vertical">
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
                    <YAxis type="category" dataKey="name" width={70} tick={{ fontSize: 10, fill: theme.global.textSecondary }} />
                    <Tooltip {...tooltipStyle(theme)} formatter={(value) => [`${value}%`, '進度']} />
                    <Bar dataKey="progress" radius={[0, 4, 4, 0]}>
                      {agentProgressData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartPanel>

              <ChartPanel title="代理狀態分佈" theme={theme}>
                <ResponsiveContainer width="100%" height={120}>
                  <PieChart>
                    <Pie data={statusDistData} cx="50%" cy="50%" innerRadius={30} outerRadius={50} dataKey="value" stroke="none">
                      {statusDistData.map((entry, i) => (
                        <Cell key={i} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip {...tooltipStyle(theme)} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="flex justify-center gap-3 mt-1">
                  {statusDistData.map((d) => (
                    <span key={d.name} className="flex items-center gap-1 text-[10px]" style={{ color: theme.global.textSecondary }}>
                      <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: d.color }} />
                      {d.name} {d.value}
                    </span>
                  ))}
                </div>
              </ChartPanel>
            </div>
          )}

          {/* 分析結果圖表（主要內容） */}
          {analysisResults.length > 0 && (
            <div className="grid grid-cols-2 xl:grid-cols-3 gap-3 mb-4">
              {analysisResults.map((result, i) => (
                <AnalysisChart key={i} result={result} theme={theme} />
              ))}
            </div>
          )}

          {/* 從日誌提取的即時指標 */}
          {extractedMetrics.length > 0 && (
            <div className="mb-4">
              <h3 className="text-[10px] font-semibold mb-2" style={{ color: theme.global.textSecondary }}>
                分析指標
              </h3>
              <div className="grid grid-cols-4 xl:grid-cols-6 gap-2">
                {extractedMetrics.slice(-12).map((m, i) => (
                  <div
                    key={i}
                    className="rounded-lg border px-2 py-1.5"
                    style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
                  >
                    <div className="text-[9px]" style={{ color: theme.global.textMuted }}>{m.agent}</div>
                    <div className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>{m.name}</div>
                    <div className="text-sm font-bold" style={{ color: theme.global.accent }}>{m.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 等待任務開始 */}
          {analysisResults.length === 0 && !isCompleted && displayAgents.length === 0 && (
            <div
              className="flex flex-col items-center justify-center h-48 rounded-xl border border-dashed"
              style={{ borderColor: theme.global.border, color: theme.global.textMuted }}
            >
              <div className="text-3xl mb-2 opacity-30">&#128202;</div>
              <div className="text-xs">任務啟動後將在此顯示分析結果</div>
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
          {Math.round(agent.progress ?? 0)}%
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

/* ── 圖表通用元件 ── */

function tooltipStyle(theme: import('../themes').WindAITheme) {
  return {
    contentStyle: {
      backgroundColor: theme.global.panelBg,
      border: `1px solid ${theme.global.border}`,
      borderRadius: 8,
      fontSize: 11,
      color: theme.global.textPrimary,
    },
  }
}

function ChartPanel({ title, theme, children }: {
  title: string
  theme: import('../themes').WindAITheme
  children: React.ReactNode
}) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
    >
      <h3 className="text-xs font-semibold mb-3" style={{ color: theme.global.textSecondary }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

/** 根據 chart_type 渲染對應的圖表 */
function AnalysisChart({ result, theme }: {
  result: AnalysisResultPayload
  theme: import('../themes').WindAITheme
}) {
  const { chart_type, title, data, metadata } = result

  if (chart_type === 'scatter' || chart_type === 'power_curve') {
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="x" name={metadata?.x_label as string || 'X'} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis dataKey="y" name={metadata?.y_label as string || 'Y'} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            <Scatter data={data} fill={theme.global.accent} />
          </ScatterChart>
        </ResponsiveContainer>
        {metadata && (
          <div className="flex gap-3 mt-2 text-[10px]" style={{ color: theme.global.textMuted }}>
            {Object.entries(metadata).filter(([k]) => !k.endsWith('_label')).map(([k, v]) => (
              <span key={k}>{k}: <b style={{ color: theme.global.accent }}>{typeof v === 'number' ? v.toFixed(4) : v}</b></span>
            ))}
          </div>
        )}
      </ChartPanel>
    )
  }

  if (chart_type === 'line' || chart_type === 'trend') {
    const keys = data.length > 0 ? Object.keys(data[0]).filter(k => k !== 'x' && k !== 'name') : []
    const colors = [theme.global.accent, theme.statuses.working.dot, theme.statuses.waiting.dot, theme.statuses.error.dot]
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="x" tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            {keys.map((key, i) => (
              <Line key={key} type="monotone" dataKey={key} stroke={colors[i % colors.length]} dot={false} strokeWidth={2} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartPanel>
    )
  }

  if (chart_type === 'bar' || chart_type === 'histogram') {
    const keys = data.length > 0 ? Object.keys(data[0]).filter(k => k !== 'name' && k !== 'x') : []
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            {keys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={i === 0 ? theme.global.accent : theme.statuses.working.dot} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    )
  }

  // 預設：顯示 metadata 為數據卡片
  return (
    <ChartPanel title={title} theme={theme}>
      {metadata && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(metadata).map(([k, v]) => (
            <div key={k} className="text-center py-2">
              <div className="text-[10px]" style={{ color: theme.global.textMuted }}>{k}</div>
              <div className="text-lg font-bold" style={{ color: theme.global.accent }}>
                {typeof v === 'number' ? v.toFixed(4) : v}
              </div>
            </div>
          ))}
        </div>
      )}
    </ChartPanel>
  )
}
