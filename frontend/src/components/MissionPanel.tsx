/**
 * MissionPanel — 右側任務面板（取代 MissionView 的右側）。
 *
 * 執行中：即時訊息流 + 頂部迷你進度條
 * 完成後：結果圖表 grid + metrics + 「查看完整記錄」按鈕
 */

import { useMemo, useRef, useEffect } from 'react'
import { useTheme, getTierColor } from '../themes'
import { AnalysisChart } from './AnalysisCharts'
import { extractMetricsFromLogs } from '../utils/extractMetrics'
import type { Agent, WorkLog, AnalysisResultPayload } from '../types/agent'

interface MissionPanelProps {
  agents: Agent[]
  workLogs: WorkLog[]
  analysisResults: AnalysisResultPayload[]
  isCompleted: boolean
  isActivelyWorking: boolean
  onClose: () => void
  onViewFullRecord?: () => void
  currentTaskDescription?: string
}

export default function MissionPanel({
  agents,
  workLogs,
  analysisResults,
  isCompleted,
  isActivelyWorking,
  onClose,
  onViewFullRecord,
  currentTaskDescription,
}: MissionPanelProps) {
  const { theme } = useTheme()
  const scrollRef = useRef<HTMLDivElement>(null)

  const activeAgents = useMemo(
    () => agents.filter((a) => a.status === 'working' || a.status === 'waiting'),
    [agents],
  )

  // 完成後也要推導參與的代理
  const displayAgents = useMemo(() => {
    if (activeAgents.length > 0) return activeAgents
    const logAgentIds = new Set(workLogs.map((l) => l.agentId).filter((id) => id !== 'system'))
    return agents.filter((a) => logAgentIds.has(a.id))
  }, [activeAgents, agents, workLogs])

  const overallProgress = useMemo(() => {
    if (activeAgents.length === 0) return 0
    const sum = activeAgents.reduce((s, a) => s + (a.progress ?? 0), 0)
    return Math.round(sum / activeAgents.length)
  }, [activeAgents])

  const extractedMetrics = useMemo(() => extractMetricsFromLogs(workLogs), [workLogs])

  // 最近 100 筆日誌（倒序顯示）
  const recentLogs = useMemo(
    () => [...workLogs].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime()).slice(0, 100),
    [workLogs],
  )

  // 自動滾動到最新訊息
  useEffect(() => {
    if (scrollRef.current && isActivelyWorking) {
      scrollRef.current.scrollTop = 0 // 因為是倒序，最新在頂部
    }
  }, [workLogs.length, isActivelyWorking])

  const title = currentTaskDescription || (isCompleted ? '任務已完成' : '任務進行中')

  return (
    <div className="flex h-full flex-col" style={{ color: theme.global.textPrimary, backgroundColor: theme.global.pageBg }}>
      {/* ── Header ── */}
      <div
        className="flex items-center gap-3 px-4 py-2.5 border-b shrink-0"
        style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg }}
      >
        {/* 狀態燈 */}
        <div
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${isCompleted ? '' : isActivelyWorking ? 'animate-pulse-slow' : ''}`}
          style={{
            backgroundColor: isCompleted
              ? theme.statuses.completed.dot
              : isActivelyWorking
                ? theme.statuses.working.dot
                : theme.global.textMuted,
          }}
        />
        <div className="flex-1 min-w-0">
          <div className="text-xs font-bold truncate">{title}</div>
          <div className="text-[10px]" style={{ color: theme.global.textSecondary }}>
            {displayAgents.length} 位代理
            {isActivelyWorking && ` · ${overallProgress}%`}
          </div>
        </div>

        {/* 迷你進度條 — 僅執行中顯示 */}
        {isActivelyWorking && (
          <div className="w-24 h-1.5 rounded-full overflow-hidden shrink-0" style={{ backgroundColor: theme.global.border }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${overallProgress}%`, backgroundColor: theme.global.accent }}
            />
          </div>
        )}

        {/* 返回按鈕 — 完成後顯示 */}
        {isCompleted && (
          <button
            onClick={onClose}
            className="rounded-lg border px-3 py-1 text-xs font-medium transition-colors hover:brightness-125 shrink-0"
            style={{
              borderColor: theme.global.accent + '60',
              backgroundColor: theme.global.accent + '20',
              color: theme.global.accent,
            }}
          >
            返回總覽
          </button>
        )}
      </div>

      {/* ── 完成提示橫幅 ── */}
      {isCompleted && (
        <div
          className="px-4 py-2 text-xs font-medium border-b shrink-0"
          style={{
            borderColor: theme.global.border,
            backgroundColor: theme.statuses.completed.bg,
            color: theme.statuses.completed.dot,
          }}
        >
          任務已完成 — 以下為分析結果
        </div>
      )}

      {/* ── 主要內容 ── */}
      <div className="flex-1 overflow-y-auto" ref={scrollRef}>
        {isCompleted ? (
          /* ══ 完成模式：顯示結果圖表 + metrics ══ */
          <div className="p-4 space-y-4">
            {/* 分析圖表 */}
            {analysisResults.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold mb-3 flex items-center gap-2" style={{ color: theme.global.textSecondary }}>
                  分析結果
                  <span
                    className="rounded-full px-1.5 py-0.5 text-[9px]"
                    style={{ backgroundColor: theme.global.accent + '30', color: theme.global.accent }}
                  >
                    {analysisResults.length} 項
                  </span>
                </h3>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                  {analysisResults.map((result, i) => (
                    <AnalysisChart key={i} result={result} theme={theme} height={180} />
                  ))}
                </div>
              </div>
            )}

            {/* 提取的 metrics */}
            {extractedMetrics.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold mb-3" style={{ color: theme.global.textSecondary }}>
                  關鍵指標
                </h3>
                <div className="grid grid-cols-3 xl:grid-cols-4 gap-2">
                  {extractedMetrics.slice(0, 12).map((m, i) => (
                    <div
                      key={i}
                      className="rounded-lg border p-2.5 text-center"
                      style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg }}
                    >
                      <div className="text-[10px] mb-1" style={{ color: theme.global.textMuted }}>{m.name}</div>
                      <div className="text-base font-bold" style={{ color: theme.global.accent }}>
                        {m.value % 1 === 0 ? m.value : m.value.toFixed(4)}
                      </div>
                      <div className="text-[9px] mt-0.5" style={{ color: theme.global.textMuted }}>{m.agent}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 參與代理 */}
            {displayAgents.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold mb-2" style={{ color: theme.global.textSecondary }}>
                  參與代理
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {displayAgents.map((a) => {
                    const tc = getTierColor(theme, a.tier)
                    return (
                      <span
                        key={a.id}
                        className="rounded-full px-2 py-0.5 text-[10px] border"
                        style={{
                          borderColor: tc.primary + '40',
                          backgroundColor: tc.bg,
                          color: tc.primary,
                        }}
                      >
                        {a.icon} {a.displayName}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {/* 查看完整記錄按鈕 */}
            {onViewFullRecord && (
              <div className="pt-2 border-t" style={{ borderColor: theme.global.border }}>
                <button
                  onClick={onViewFullRecord}
                  className="w-full rounded-lg border px-4 py-2 text-xs font-medium transition-colors hover:brightness-110"
                  style={{
                    borderColor: theme.global.border,
                    backgroundColor: theme.global.panelBg,
                    color: theme.global.textSecondary,
                  }}
                >
                  🗂️ 查看歷史記錄
                </button>
              </div>
            )}

            {/* 空狀態 */}
            {analysisResults.length === 0 && extractedMetrics.length === 0 && (
              <div className="text-center py-12">
                <div className="text-2xl mb-2">📊</div>
                <div className="text-xs" style={{ color: theme.global.textMuted }}>
                  此任務未產出分析圖表
                </div>
              </div>
            )}
          </div>
        ) : (
          /* ══ 執行中：即時訊息流 ══ */
          <div className="p-3">
            <div className="text-[10px] font-semibold mb-2 px-1" style={{ color: theme.global.textSecondary }}>
              即時訊息
            </div>
            <div className="space-y-0.5">
              {recentLogs.length === 0 ? (
                <div className="text-center py-8 text-xs" style={{ color: theme.global.textMuted }}>
                  等待任務訊息...
                </div>
              ) : (
                recentLogs.map((log) => (
                  <LogEntry key={log.id} log={log} theme={theme} />
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── LogEntry sub-component ── */

function LogEntry({ log, theme }: { log: WorkLog; theme: import('../themes').WindAITheme }) {
  const typeColor = {
    info: theme.global.textSecondary,
    success: theme.statuses.completed.dot,
    warning: theme.statuses.waiting.dot,
    error: theme.statuses.error.dot,
  }[log.type]

  const ts = log.timestamp
  const timeStr = `${ts.getHours().toString().padStart(2, '0')}:${ts.getMinutes().toString().padStart(2, '0')}:${ts.getSeconds().toString().padStart(2, '0')}`

  return (
    <div className="flex gap-2 py-0.5 text-[10px] leading-relaxed">
      <span className="shrink-0 font-mono" style={{ color: theme.global.textMuted }}>
        {timeStr}
      </span>
      <span className="shrink-0 font-semibold" style={{ color: typeColor }}>
        {log.agentName}
      </span>
      <span className="truncate" style={{ color: theme.global.textSecondary }}>
        {log.message}
      </span>
    </div>
  )
}
