/**
 * WorkflowProgress — 任務執行步驟進度條。
 *
 * 取代純文字日誌流，以步驟條視覺化顯示目前進度。
 * 根據代理狀態推斷目前走到哪一步。
 */

import { useMemo, useRef, useEffect, useState } from 'react'
import { useTheme, getStatusColor, getTierColor } from '../themes'
import type { Agent, WorkLog, AnalysisResultPayload, WorkflowRetryEvent, WorkflowDegradationEvent, WorkflowCheckpointEvent } from '../types/agent'
import { AnalysisChart } from './AnalysisCharts'

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
    // 當前步驟進度由 active agent 的 progress 決定
    const avgAgentProgress = activeAgents.length > 0
      ? activeAgents.reduce((s, a) => s + (a.progress ?? 0), 0) / activeAgents.length
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

  return (
    <div className="flex h-full flex-col">
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: theme.global.border }}
      >
        <div className="flex items-center gap-3">
          <span className="text-base">{isCompleted ? '✅' : '🚀'}</span>
          <div>
            <div className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
              {currentTaskDescription || '任務執行中'}
            </div>
            <div className="text-[10px]" style={{ color: theme.global.textMuted }}>
              {isCompleted ? '已完成' : isActivelyWorking ? `進行中 · ${formatTime(elapsed)}` : '準備中'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
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
            {isCompleted ? '關閉' : '收起'}
          </button>
        </div>
      </div>

      {/* ── 整體進度條 ── */}
      <div className="px-4 py-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px]" style={{ color: theme.global.textSecondary }}>
            {overallProgress}%
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
                  {a.progress != null && ` ${Math.round(a.progress * 100)}%`}
                </span>
              ))}
            </div>
          )}
        </div>
        <div
          className="h-1.5 w-full rounded-full overflow-hidden"
          style={{ backgroundColor: theme.global.border }}
        >
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${overallProgress}%`,
              backgroundColor: isCompleted ? getStatusColor(theme, 'completed').dot : getStatusColor(theme, 'working').dot,
            }}
          />
        </div>
      </div>

      {/* ── 步驟條 ── */}
      {steps.length > 0 && (
        <div className="px-4 py-2 flex items-center gap-1 overflow-x-auto">
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
      {workflowEvents.length > 0 && (() => {
        const latestEvent = workflowEvents[workflowEvents.length - 1]

        // Checkpoint 事件
        if ('status' in latestEvent && 'description' in latestEvent) {
          const cp = latestEvent as WorkflowCheckpointEvent
          const isEval = cp.status === 'evaluating'
          const isPassed = cp.status === 'passed' || cp.status === 'passed_after_rerun'
          const isFailed = cp.status === 'failed'
          const isRerun = cp.status === 'rerunning'
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
              className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px]"
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

        // Retry 事件
        if ('attempt' in latestEvent && 'max_retries' in latestEvent) {
          const rt = latestEvent as WorkflowRetryEvent
          return (
            <div
              className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px]"
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

        // Degradation 事件
        if ('strategy' in latestEvent) {
          const dg = latestEvent as WorkflowDegradationEvent
          const icon = dg.strategy === 'skip' ? '⏭️' : dg.strategy === 'fallback' ? '🔀' : '⛔'
          const label = dg.strategy === 'skip' ? '已跳過' : dg.strategy === 'fallback' ? '降級至備用代理' : '工作流程中止'
          const fgColor = dg.strategy === 'abort' ? '#ef4444' : '#f59e0b'
          return (
            <div
              className="mx-4 my-1 flex items-center gap-2 rounded-md px-3 py-1.5 text-[10px]"
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
      })()}

      {/* ── 最新動態（一行） ── */}
      {latestLog && !showLogs && (
        <div
          className="px-4 py-1.5 text-[10px] truncate cursor-pointer hover:opacity-80"
          style={{ color: theme.global.textSecondary }}
          onClick={() => setShowLogs(true)}
        >
          <span style={{ color: getStatusColor(theme, latestLog.type === 'error' ? 'error' : latestLog.type === 'success' ? 'completed' : 'idle').dot }}>
            ●
          </span>{' '}
          {latestLog.agentName}：{latestLog.message}
          <span style={{ color: theme.global.textMuted }}> · 點擊展開日誌</span>
        </div>
      )}

      {/* ── 分析結果（完成後） ── */}
      {isCompleted && analysisResults.length > 0 && (
        <div className="flex-1 overflow-y-auto px-4 py-2">
          <div className="text-[10px] font-medium mb-2" style={{ color: theme.global.textSecondary }}>
            分析結果
          </div>
          <div className="grid grid-cols-2 gap-3">
            {analysisResults.map((r, i) => (
              <AnalysisChart key={i} result={r} theme={theme} />
            ))}
          </div>
        </div>
      )}

      {/* ── 展開的日誌面板 ── */}
      {showLogs && (
        <div className="flex-1 overflow-hidden flex flex-col border-t" style={{ borderColor: theme.global.border }}>
          <div className="flex items-center justify-between px-4 py-1.5">
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

      {/* 沒有日誌也沒有結果時的佔位 */}
      {!isActivelyWorking && !isCompleted && workLogs.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <span className="text-xs" style={{ color: theme.global.textMuted }}>等待任務啟動...</span>
        </div>
      )}
    </div>
  )
}
