/**
 * TaskHistoryList — 任務歷史記錄列表元件。
 *
 * 在 DashboardView 的「歷史記錄」tab 中渲染。
 * 每筆記錄可展開查看圖表、metrics 和 work logs。
 */

import { useState } from 'react'
import { useTheme } from '../themes'
import { AnalysisChart } from './AnalysisCharts'
import type { TaskRecord } from '../types/agent'

interface TaskHistoryListProps {
  records: TaskRecord[]
  onDeleteRecord: (id: string) => void
  onClearAll: () => void
}

export default function TaskHistoryList({ records, onDeleteRecord, onClearAll }: TaskHistoryListProps) {
  const { theme } = useTheme()
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirmClear, setConfirmClear] = useState(false)

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  const handleClearAll = () => {
    if (confirmClear) {
      onClearAll()
      setConfirmClear(false)
    } else {
      setConfirmClear(true)
      setTimeout(() => setConfirmClear(false), 3000)
    }
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    const s = Math.round(ms / 1000)
    if (s < 60) return `${s}s`
    return `${Math.floor(s / 60)}m ${s % 60}s`
  }

  const formatTimestamp = (iso: string) => {
    const d = new Date(iso)
    return `${d.getFullYear()}/${(d.getMonth() + 1).toString().padStart(2, '0')}/${d.getDate().toString().padStart(2, '0')} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }

  if (records.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="text-3xl mb-3">🗂️</div>
        <div className="text-sm font-medium" style={{ color: theme.global.textSecondary }}>
          尚無歷史記錄
        </div>
        <div className="text-xs mt-1" style={{ color: theme.global.textMuted }}>
          執行任務後結果會自動保存至此
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* 工具列 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold" style={{ color: theme.global.textSecondary }}>
            歷史記錄
          </span>
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px]"
            style={{ backgroundColor: theme.global.border, color: theme.global.textSecondary }}
          >
            {records.length} 筆
          </span>
        </div>
        <button
          onClick={handleClearAll}
          className="rounded px-2 py-1 text-[10px] transition-colors hover:brightness-125"
          style={{
            backgroundColor: confirmClear ? theme.statuses.error.bg : 'transparent',
            color: confirmClear ? theme.statuses.error.dot : theme.global.textMuted,
            border: confirmClear ? `1px solid ${theme.statuses.error.dot}40` : '1px solid transparent',
          }}
        >
          {confirmClear ? '確認清除全部？' : '清除全部'}
        </button>
      </div>

      {/* 記錄列表 */}
      {records.map((record) => {
        const isExpanded = expandedId === record.id
        return (
          <div
            key={record.id}
            className="rounded-xl border overflow-hidden"
            style={{
              borderColor: isExpanded ? theme.global.accent + '60' : theme.global.border,
              backgroundColor: theme.global.panelBg,
            }}
          >
            {/* 摘要行 — 可點擊展開 */}
            <button
              onClick={() => toggleExpand(record.id)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:brightness-110"
            >
              {/* 狀態燈 */}
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{
                  backgroundColor: record.status === 'completed'
                    ? theme.statuses.completed.dot
                    : theme.statuses.error.dot,
                }}
              />

              {/* 時間 */}
              <span className="text-[10px] font-mono shrink-0" style={{ color: theme.global.textMuted }}>
                {formatTimestamp(record.timestamp)}
              </span>

              {/* 描述 */}
              <span className="flex-1 text-xs font-medium truncate" style={{ color: theme.global.textPrimary }}>
                {record.description}
              </span>

              {/* badges */}
              <span className="text-[9px] shrink-0" style={{ color: theme.global.textMuted }}>
                {record.agentNames.length} 代理
              </span>
              <span className="text-[9px] shrink-0" style={{ color: theme.global.textMuted }}>
                {formatDuration(record.durationMs)}
              </span>
              {record.analysisResults.length > 0 && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[9px] shrink-0"
                  style={{ backgroundColor: theme.global.accent + '20', color: theme.global.accent }}
                >
                  {record.analysisResults.length} 圖表
                </span>
              )}

              {/* 箭頭 */}
              <svg
                className={`w-3.5 h-3.5 shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                style={{ color: theme.global.textMuted }}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* 展開內容 */}
            {isExpanded && (
              <div className="border-t px-4 py-3 space-y-4" style={{ borderColor: theme.global.border }}>
                {/* 參與代理 */}
                <div>
                  <div className="text-[10px] font-semibold mb-1.5" style={{ color: theme.global.textSecondary }}>
                    參與代理
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {record.agentNames.map((name, i) => (
                      <span
                        key={i}
                        className="rounded-full px-2 py-0.5 text-[10px] border"
                        style={{ borderColor: theme.global.border, color: theme.global.textSecondary }}
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                </div>

                {/* 圖表 */}
                {record.analysisResults.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold mb-2" style={{ color: theme.global.textSecondary }}>
                      分析結果
                    </div>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-2">
                      {record.analysisResults.map((result, i) => (
                        <AnalysisChart key={i} result={result} theme={theme} height={150} />
                      ))}
                    </div>
                  </div>
                )}

                {/* Metrics */}
                {record.extractedMetrics.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold mb-2" style={{ color: theme.global.textSecondary }}>
                      關鍵指標
                    </div>
                    <div className="grid grid-cols-3 xl:grid-cols-4 gap-1.5">
                      {record.extractedMetrics.map((m, i) => (
                        <div
                          key={i}
                          className="rounded-lg border p-2 text-center"
                          style={{ borderColor: theme.global.border }}
                        >
                          <div className="text-[9px]" style={{ color: theme.global.textMuted }}>{m.name}</div>
                          <div className="text-sm font-bold" style={{ color: theme.global.accent }}>
                            {m.value % 1 === 0 ? m.value : m.value.toFixed(4)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Work log 最近 20 筆 */}
                {record.workLogSnapshot.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold mb-1.5" style={{ color: theme.global.textSecondary }}>
                      工作日誌（最近 {Math.min(20, record.workLogSnapshot.length)} 筆）
                    </div>
                    <div
                      className="rounded-lg border p-2 max-h-40 overflow-y-auto space-y-0.5"
                      style={{ borderColor: theme.global.border }}
                    >
                      {record.workLogSnapshot.slice(-20).reverse().map((log, i) => {
                        const ts = new Date(log.timestamp)
                        const timeStr = `${ts.getHours().toString().padStart(2, '0')}:${ts.getMinutes().toString().padStart(2, '0')}:${ts.getSeconds().toString().padStart(2, '0')}`
                        const typeColor = {
                          info: theme.global.textSecondary,
                          success: theme.statuses.completed.dot,
                          warning: theme.statuses.waiting.dot,
                          error: theme.statuses.error.dot,
                        }[log.type]
                        return (
                          <div key={i} className="flex gap-2 text-[9px] leading-relaxed">
                            <span className="shrink-0 font-mono" style={{ color: theme.global.textMuted }}>
                              {timeStr}
                            </span>
                            <span className="shrink-0 font-semibold" style={{ color: typeColor }}>
                              {log.agentName}
                            </span>
                            <span className="truncate" style={{ color: theme.global.textMuted }}>
                              {log.message}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* 刪除按鈕 */}
                <div className="flex justify-end pt-1">
                  <button
                    onClick={() => onDeleteRecord(record.id)}
                    className="rounded px-2 py-1 text-[10px] transition-colors hover:brightness-125"
                    style={{ color: theme.statuses.error.dot }}
                  >
                    刪除此記錄
                  </button>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
