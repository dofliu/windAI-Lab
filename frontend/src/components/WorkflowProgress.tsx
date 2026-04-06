/**
 * WorkflowProgress — 戰情中心主元件。
 *
 * Phase 11 升級：三欄佈局
 * - 左欄：參與代理面板（MissionAgentPanel）
 * - 中欄：進度條 + 步驟條 + 日誌
 * - 右欄：即時分析結果圖表
 *
 * 任務進行中與完成後均保持顯示，讓使用者查看完整結果。
 */

import { useMemo, useRef, useEffect, useState } from 'react'
import { useTheme, getStatusColor, getTierColor } from '../themes'
import type { Agent, WorkLog, AnalysisResultPayload, WorkflowRetryEvent, WorkflowDegradationEvent, WorkflowCheckpointEvent } from '../types/agent'
import { AnalysisChart } from './AnalysisCharts'
import MissionAgentPanel from './MissionAgentPanel'

interface WorkflowProgressProps {
  agents: Agent[]
  workLogs: WorkLog[]
  analysisResults: AnalysisResultPayload[]
  isActivelyWorking: boolean
  isCompleted: boolean
  onClose: () => void
  onViewFullRecord?: () => void
  currentTaskDescription?: string
  workflowEvents?: Array<WorkflowRetryEvent | WorkflowDegradationEvent | WorkflowCheckpointEvent>
}

export default function WorkflowProgress({
  agents,
  workLogs,
  analysisResults,
  isActivelyWorking,
  isCompleted,
  onClose,
  onViewFullRecord,
  currentTaskDescription,
  workflowEvents = [],
}: WorkflowProgressProps) {
  const { theme } = useTheme()
  const logEndRef = useRef<HTMLDivElement>(null)
  const [showLogs, setShowLogs] = useState(false)
  const [showAgentPanel, setShowAgentPanel] = useState(true)

  const activeAgents = useMemo(
    () => agents.filter((a) => a.status === 'working' || a.status === 'waiting'),
    [agents],
  )

  // 從工作日誌推斷步驟
  const steps = useMemo(() => {
    const systemLogs = workLogs.filter(
      (l) => l.agentId === 'system' && l.message.match(/^\[?\d+\/\d+\]?\s|📋/)
    )
    return systemLogs.map((l, i) => {
      const match = l.message.match(/\[(\d+)\/(\d+)\]\s+(.+)/)
      return {
        index: i,
        label: match ? match[3] : l.message.replace(/^📋\s*/, ''),
        stepNum: match ? parseInt(match[1]) : i + 1,
        totalSteps: match ? parseInt(match[2]) : systemLogs.length,
        timestamp: l.timestamp,
      }
    })
  }, [workLogs])

  const totalSteps = steps.length > 0 ? steps[steps.length - 1].totalSteps : 0
  const currentStepNum = steps.length

  // 計算整體進度
  const overallProgress = useMemo(() => {
    if (isCompleted) return 100
    if (totalSteps === 0) return 0
    const avgAgentProgress = activeAgents.length > 0
      ? activeAgents.reduce((s, a) => s + (a.progress ?? 0), 0) / activeAgents.length / 100
      : 0
    return Math.round(((currentStepNum - 1 + avgAgentProgress) / totalSteps) * 100)
  }, [isCompleted, totalSteps, currentStepNum, activeAgents])

  // 最近日誌
  const recentLogs = useMemo(
    () => workLogs.filter((l) => l.agentId !== 'system').slice(-30).reverse(),
    [workLogs],
  )

  const latestLog = recentLogs[0]

  // 自動捲到底部
  useEffect(() => {
    if (showLogs) logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [workLogs.length, showLogs])

  // 經過時間
  const [elapsed, setElapsed] = useState(0)
  const startTime = useRef(Date.now())
  useEffect(() => {
    if (!isActivelyWorking && !isCompleted) {
      startTime.current = Date.now()
    }
    if (!isActivelyWorking) return
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startTime.current) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [isActivelyWorking])

  const formatTime = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  // 即時分析結果（任務進行中也顯示）
  const hasResults = analysisResults.length > 0

  return (
    <div className="flex h-full flex-col">
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b shrink-0"
        style={{ borderColor: theme.global.border }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{
              backgroundColor: isCompleted
                ? getStatusColor(theme, 'completed').dot + '20'
                : getStatusColor(theme, 'working').dot + '20',
            }}
          >
            <span className="text-sm">{isCompleted ? '\u2705' : '\u{1F680}'}</span>
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
              {currentTaskDescription || '任務執行中'}
            </div>
            <div className="text-[10px] flex items-center gap-2" style={{ color: theme.global.textMuted }}>
              <span>
                {isCompleted ? '已完成' : isActivelyWorking ? `進行中 · ${formatTime(elapsed)}` : '準備中'}
              </span>
              {activeAgents.length > 0 && (
                <span>· {activeAgents.length} 位代理工作中</span>
              )}
              {hasResults && (
                <span>· {analysisResults.length} 項分析結果</span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowAgentPanel(!showAgentPanel)}
            className="rounded px-2 py-1 text-[10px] transition-colors hover:brightness-125"
            style={{
              backgroundColor: showAgentPanel ? theme.global.accent + '15' : 'transparent',
              color: showAgentPanel ? theme.global.accent : theme.global.textMuted,
            }}
            title={showAgentPanel ? '隱藏代理面板' : '顯示代理面板'}
          >
            👥 代理
          </button>
          {isCompleted && onViewFullRecord && (
            <button
              onClick={onViewFullRecord}
              className="rounded px-2 py-1 text-[10px] transition-colors hover:brightness-125"
              style={{ backgroundColor: theme.global.accent + '20', color: theme.global.accent }}
            >
              查看完整記錄
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded px-2 py-1 text-[10px] transition-colors hover:brightness-125"
            style={{ color: theme.global.textMuted }}
          >
            {isCompleted ? '✕ 關閉' : '收起'}
          </button>
        </div>
      </div>

      {/* ── 整體進度條 ── */}
      <div className="px-4 py-2 shrink-0">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>
            {overallProgress}% 完成
          </span>
          {activeAgents.length > 0 && (
            <div className="flex items-center gap-1">
              {activeAgents.map((a) => (
                <span
                  key={a.id}
                  className="flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px]"
                  style={{
                    backgroundColor: getTierColor(theme, a.tier).primary + '20',
                    color: getTierColor(theme, a.tier).primary,
                  }}
                >
                  {a.displayName}
                  {a.progress != null && ` ${a.progress}%`}
                </span>
              ))}
            </div>
          )}
        </div>
        <div
          className="h-2 w-full rounded-full overflow-hidden"
          style={{ backgroundColor: theme.global.border }}
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${overallProgress}%`,
              backgroundColor: isCompleted ? getStatusColor(theme, 'completed').dot : getStatusColor(theme, 'working').dot,
              boxShadow: isActivelyWorking ? `0 0 8px ${getStatusColor(theme, 'working').dot}60` : 'none',
            }}
          />
        </div>
      </div>

      {/* ── 步驟條 ── */}
      {steps.length > 0 && (
        <div className="px-4 py-1.5 flex items-center gap-1 overflow-x-auto shrink-0">
          {steps.map((step, i) => {
            const isDone = i < currentStepNum - 1 || isCompleted
            const isCurrent = i === currentStepNum - 1 && !isCompleted
            return (
              <div key={i} className="flex items-center gap-1 shrink-0">
                {i > 0 && (
                  <div
                    className="w-4 h-px"
                    style={{
                      backgroundColor: isDone ? getStatusColor(theme, 'working').dot : theme.global.border,
                    }}
                  />
                )}
                <div
                  className="flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-medium whitespace-nowrap transition-all"
                  style={{
                    backgroundColor: isCurrent
                      ? getStatusColor(theme, 'working').dot + '20'
                      : isDone
                        ? getStatusColor(theme, 'completed').dot + '15'
                        : theme.global.border + '40',
                    color: isCurrent
                      ? getStatusColor(theme, 'working').dot
                      : isDone
                        ? getStatusColor(theme, 'completed').dot
                        : theme.global.textMuted,
                    border: isCurrent ? `1px solid ${getStatusColor(theme, 'working').dot}40` : '1px solid transparent',
                  }}
                >
                  {isDone ? '✓' : isCurrent ? '●' : '○'} {step.label}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Checkpoint / Retry 狀態 ── */}
      {workflowEvents.length > 0 && <WorkflowEventBadge event={workflowEvents[workflowEvents.length - 1]} />}

      {/* ── 主內容區：代理面板 + 日誌/結果 ── */}
      <div className="flex flex-1 overflow-hidden border-t" style={{ borderColor: theme.global.border + '60' }}>
        {/* 左：代理面板 */}
        {showAgentPanel && (
          <div
            className="w-56 shrink-0 border-r overflow-y-auto p-2"
            style={{ borderColor: theme.global.border + '40' }}
          >
            <MissionAgentPanel
              agents={agents}
              workLogs={workLogs}
              isCompleted={isCompleted}
            />
          </div>
        )}

        {/* 中：日誌 + 即時動態 */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* 最新動態（一行） */}
          {latestLog && !showLogs && (
            <div
              className="px-4 py-1.5 text-[10px] truncate cursor-pointer hover:opacity-80 shrink-0 border-b"
              style={{ color: theme.global.textSecondary, borderColor: theme.global.border + '30' }}
              onClick={() => setShowLogs(true)}
            >
              <span style={{ color: getStatusColor(theme, latestLog.type === 'error' ? 'error' : latestLog.type === 'success' ? 'completed' : 'idle').dot }}>
                ●
              </span>{' '}
              {latestLog.agentName}：{latestLog.message}
              <span style={{ color: theme.global.textMuted }}> · 點擊展開日誌</span>
            </div>
          )}

          {/* 展開的日誌面板 */}
          {showLogs && (
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-4 py-1.5 shrink-0">
                <span className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>
                  工作日誌 ({workLogs.length})
                </span>
                <button
                  onClick={() => setShowLogs(false)}
                  className="text-[10px] hover:brightness-125"
                  style={{ color: theme.global.textMuted }}
                >
                  收合 ▲
                </button>
              </div>
              <div className="flex-1 overflow-y-auto px-4 pb-2 space-y-0.5">
                {workLogs.slice(-50).map((log) => (
                  <div key={log.id} className="flex items-start gap-2 text-[10px] py-0.5">
                    <span
                      className="shrink-0 w-1.5 h-1.5 rounded-full mt-1"
                      style={{
                        backgroundColor: log.type === 'error'
                          ? getStatusColor(theme, 'error').dot
                          : log.type === 'success'
                            ? getStatusColor(theme, 'completed').dot
                            : theme.global.textMuted,
                      }}
                    />
                    <span className="shrink-0 font-medium w-16 truncate" style={{ color: theme.global.textSecondary }}>
                      {log.agentName}
                    </span>
                    <span style={{ color: theme.global.textPrimary }}>{log.message}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          )}

          {/* 非日誌模式：分析結果或佔位 */}
          {!showLogs && (
            <div className="flex-1 overflow-y-auto">
              {hasResults ? (
                <div className="p-4">
                  <div className="text-[10px] font-medium mb-2" style={{ color: theme.global.textSecondary }}>
                    {isCompleted ? '分析結果' : '即時分析結果'}
                    <span style={{ color: theme.global.textMuted }}> ({analysisResults.length})</span>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {analysisResults.map((r, i) => (
                      <AnalysisChart key={i} result={r} theme={theme} height={180} />
                    ))}
                  </div>
                </div>
              ) : (
                !isActivelyWorking && !isCompleted && workLogs.length === 0 && (
                  <div className="flex-1 flex items-center justify-center h-full">
                    <div className="text-center">
                      <span className="text-2xl block mb-2">🚀</span>
                      <span className="text-xs" style={{ color: theme.global.textMuted }}>
                        等待任務啟動...
                      </span>
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Checkpoint / Retry / Degradation 事件標籤 ── */

function WorkflowEventBadge({
  event,
}: {
  event: WorkflowRetryEvent | WorkflowDegradationEvent | WorkflowCheckpointEvent
}) {
  // Checkpoint
  if ('status' in event && 'description' in event) {
    const cp = event as WorkflowCheckpointEvent
    const isPassed = cp.status === 'passed' || cp.status === 'passed_after_rerun'
    const isFailed = cp.status === 'failed'
    const isRerun = cp.status === 'rerunning'
    const isEval = cp.status === 'evaluating'
    const bgColor = isPassed ? '#10b98120' : isFailed ? '#ef444420' : isRerun ? '#f59e0b20' : '#6366f120'
    const fgColor = isPassed ? '#10b981' : isFailed ? '#ef4444' : isRerun ? '#f59e0b' : '#6366f1'
    const icon = isPassed ? '✅' : isFailed ? '❌' : isRerun ? '🔄' : '🔍'
    const label = isPassed
      ? `品質合格${cp.status === 'passed_after_rerun' ? '（重跑後）' : ''}`
      : isFailed
        ? `品質未達標${cp.violations ? ' — ' + cp.violations.map(v => `${v.metric}: ${v.value.toFixed(3)} < ${v.threshold}`).join(', ') : ''}`
        : isRerun
          ? `調參重跑中 (${cp.rerun}/${cp.max_reruns})`
          : `總監評估中：${cp.description || ''}`

    return (
      <div
        className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px] shrink-0"
        style={{ backgroundColor: bgColor, color: fgColor }}
      >
        <span>{icon}</span>
        <span className="font-medium">Checkpoint</span>
        <span style={{ color: fgColor + 'cc' }}>{cp.step_name}</span>
        <span className="flex-1 truncate">{label}</span>
        {isEval && <span className="animate-pulse">●</span>}
      </div>
    )
  }

  // Retry
  if ('attempt' in event && 'max_retries' in event) {
    const rt = event as WorkflowRetryEvent
    return (
      <div
        className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px] shrink-0"
        style={{ backgroundColor: '#f59e0b20', color: '#f59e0b' }}
      >
        <span>🔄</span>
        <span className="font-medium">重試</span>
        <span>{rt.step_name}</span>
        <span>第 {rt.attempt}/{rt.max_retries} 次</span>
        <span style={{ color: '#f59e0baa' }}>({rt.delay_seconds}s 後)</span>
      </div>
    )
  }

  // Degradation
  if ('strategy' in event) {
    const dg = event as WorkflowDegradationEvent
    const icon = dg.strategy === 'skip' ? '⏭️' : dg.strategy === 'fallback' ? '🔀' : '⛔'
    const label = dg.strategy === 'skip' ? '已跳過' : dg.strategy === 'fallback' ? '降級至備用代理' : '工作流程中止'
    const fgColor = dg.strategy === 'abort' ? '#ef4444' : '#f59e0b'
    return (
      <div
        className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px] shrink-0"
        style={{ backgroundColor: fgColor + '20', color: fgColor }}
      >
        <span>{icon}</span>
        <span className="font-medium">{label}</span>
        <span>{dg.step_name}</span>
        {dg.reason && <span className="truncate" style={{ color: fgColor + 'aa' }}>{dg.reason}</span>}
      </div>
    )
  }

  return null
}
