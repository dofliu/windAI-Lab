/**
 * extractMetrics — 從工作日誌中提取數值指標的共用工具。
 *
 * 供 MissionPanel、App（任務記錄存檔）、TaskHistoryList 共用。
 */

import type { WorkLog } from '../types/agent'

export interface ExtractedMetric {
  name: string
  value: number
  agent: string
  timestamp: number
}

export interface SerializedWorkLog {
  id: string
  timestamp: string  // ISO string
  agentId: string
  agentName: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

const METRIC_PATTERNS = [
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

/** 掃描 workLogs 訊息，提取所有數值指標 */
export function extractMetricsFromLogs(logs: WorkLog[]): ExtractedMetric[] {
  const metrics: ExtractedMetric[] = []
  logs.forEach((log) => {
    METRIC_PATTERNS.forEach(({ regex, name }) => {
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
}

/** 將 WorkLog（含 Date）序列化為 JSON 安全格式 */
export function serializeWorkLog(log: WorkLog): SerializedWorkLog {
  return {
    id: log.id,
    timestamp: log.timestamp.toISOString(),
    agentId: log.agentId,
    agentName: log.agentName,
    message: log.message,
    type: log.type,
  }
}
