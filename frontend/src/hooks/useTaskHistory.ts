/**
 * useTaskHistory — 任務歷史記錄持久化 hook。
 *
 * 使用 localStorage 儲存已完成任務的結果，供後續查閱。
 */

import { useState, useEffect, useCallback } from 'react'
import type { TaskRecord } from '../types/agent'

const STORAGE_KEY = 'windai_task_history'
const MAX_RECORDS = 50

export function useTaskHistory() {
  const [records, setRecords] = useState<TaskRecord[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : []
    } catch {
      return []
    }
  })

  // 持久化到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(records))
    } catch {
      // quota exceeded — 靜默忽略
    }
  }, [records])

  const saveRecord = useCallback((record: TaskRecord) => {
    setRecords((prev) => {
      const next = [record, ...prev]
      return next.length > MAX_RECORDS ? next.slice(0, MAX_RECORDS) : next
    })
  }, [])

  const deleteRecord = useCallback((id: string) => {
    setRecords((prev) => prev.filter((r) => r.id !== id))
  }, [])

  const clearRecords = useCallback(() => setRecords([]), [])

  return { records, saveRecord, deleteRecord, clearRecords }
}
