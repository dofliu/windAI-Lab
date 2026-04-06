/**
 * useTaskHistory — 任務歷史記錄持久化 hook。
 *
 * 雙層儲存：
 * - localStorage：前端即時記錄（模擬模式 + 即時結果）
 * - 後端 API：持久化記錄（後端資料庫，重啟不消失）
 *
 * 顯示時合併兩者，以 ID 去重。
 */

import { useState, useEffect, useCallback } from 'react'
import type { TaskRecord } from '../types/agent'

const STORAGE_KEY = 'windai_task_history'
const MAX_RECORDS = 50
const API_BASE = 'http://localhost:8000/api'

/** 後端任務記錄格式 */
interface BackendTask {
  id: string
  command: string
  description: string
  status: string
  started_at: string
  completed_at: string | null
  duration_ms: number
  agent_ids: string[]
  agent_names: string[]
  parameters: Record<string, unknown>
  error_message: string | null
}

/** 將後端記錄轉為前端 TaskRecord 格式 */
function backendToTaskRecord(t: BackendTask): TaskRecord {
  return {
    id: t.id,
    description: t.description || t.command,
    timestamp: t.started_at,
    durationMs: t.duration_ms,
    agentIds: t.agent_ids || [],
    agentNames: t.agent_names || [],
    analysisResults: (t as any).analysis_results || [],
    extractedMetrics: [],
    workLogSnapshot: [],
    status: t.status === 'completed' ? 'completed' : 'error',
  }
}

export function useTaskHistory() {
  const [localRecords, setLocalRecords] = useState<TaskRecord[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })

  const [backendRecords, setBackendRecords] = useState<TaskRecord[]>([])

  // 持久化到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(localRecords))
    } catch {
      // quota exceeded — 靜默忽略
    }
  }, [localRecords])

  // 從後端拉取歷史記錄
  const fetchBackendHistory = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks/history?limit=50`)
      if (res.ok) {
        const data = await res.json()
        const tasks: BackendTask[] = data.tasks || []
        setBackendRecords(tasks.map(backendToTaskRecord))
      }
    } catch {
      // 後端離線 — 靜默忽略
    }
  }, [])

  // 啟動時拉取一次，之後每 30 秒更新
  useEffect(() => {
    fetchBackendHistory()
    const timer = setInterval(fetchBackendHistory, 30000)
    return () => clearInterval(timer)
  }, [fetchBackendHistory])

  // 合併：前端優先（有完整 analysisResults），後端補充
  // 除了 ID 去重外，也按 description + 時間近似去重（2 分鐘內同描述 = 同任務）
  const records = (() => {
    const merged: TaskRecord[] = []
    const seen = new Set<string>()
    const timeKeys = new Set<string>()

    const toTimeKey = (r: TaskRecord) => {
      const t = Math.floor(new Date(r.timestamp).getTime() / 120000) // 2 分鐘區間
      return `${r.description}@${t}`
    }

    // 前端記錄優先（有 analysisResults）
    for (const r of localRecords) {
      seen.add(r.id)
      timeKeys.add(toTimeKey(r))
      merged.push(r)
    }
    // 後端記錄補充（同 ID 或同描述+近似時間 → 跳過）
    for (const r of backendRecords) {
      if (seen.has(r.id)) continue
      if (timeKeys.has(toTimeKey(r))) continue
      seen.add(r.id)
      timeKeys.add(toTimeKey(r))
      merged.push(r)
    }
    // 按時間排序（最新在前）
    merged.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    return merged.slice(0, MAX_RECORDS)
  })()

  const saveRecord = useCallback((record: TaskRecord) => {
    setLocalRecords((prev) => {
      // 同 ID 則覆蓋（後端 task_id 與前端紀錄統一）
      const filtered = prev.filter((r) => r.id !== record.id)
      const next = [record, ...filtered]
      return next.length > MAX_RECORDS ? next.slice(0, MAX_RECORDS) : next
    })
  }, [])

  const deleteRecord = useCallback((id: string) => {
    setLocalRecords((prev) => prev.filter((r) => r.id !== id))
  }, [])

  const clearRecords = useCallback(() => setLocalRecords([]), [])

  return { records, saveRecord, deleteRecord, clearRecords }
}

