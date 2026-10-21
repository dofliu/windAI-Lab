/**
 * CaseRecommendation — 相似維修案例推薦（Epic A / Issue #49）。
 *
 * 依告警 ID 呼叫 `GET /api/cases/similar`，列出 Top-K 歷史案例，
 * 點擊可展開完整解法。無推薦或後端不可用時顯示空狀態，不影響工單面板。
 */

import { useEffect, useState } from 'react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface CaseRecommendationProps {
  alertId: string
}

interface Recommendation {
  case_id: string
  similarity: number
  fault_type: string
  solution: string
  turbine_id: string
  same_turbine: boolean
}

type LoadState = 'loading' | 'ready' | 'error'

export default function CaseRecommendation({ alertId }: CaseRecommendationProps) {
  const { theme } = useTheme()
  const [items, setItems] = useState<Recommendation[]>([])
  const [state, setState] = useState<LoadState>('loading')
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setState('loading')
    setExpanded(null)
    fetch(`${API_BASE}/cases/similar?alert_id=${encodeURIComponent(alertId)}&top_k=5`)
      .then(res => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then(data => {
        if (cancelled) return
        setItems(data.recommendations ?? [])
        setState('ready')
      })
      .catch(() => {
        if (!cancelled) setState('error')
      })
    return () => {
      cancelled = true
    }
  }, [alertId])

  return (
    <div className="space-y-1 border-t pt-2" style={{ borderColor: theme.global.border + '40' }}>
      <span className="text-[9px] font-medium" style={{ color: theme.global.textSecondary }}>
        相似歷史案例
      </span>
      {state === 'loading' && (
        <div className="text-[9px]" style={{ color: theme.global.textMuted }}>搜尋中...</div>
      )}
      {state === 'error' && (
        <div className="text-[9px]" style={{ color: theme.global.textMuted }}>暫時無法取得推薦</div>
      )}
      {state === 'ready' && items.length === 0 && (
        <div className="text-[9px]" style={{ color: theme.global.textMuted }}>尚無相似案例</div>
      )}
      {state === 'ready' &&
        items.map(item => {
          const isOpen = expanded === item.case_id
          return (
            <div key={item.case_id} className="rounded border px-2 py-1"
              style={{ borderColor: theme.global.border + '60' }}>
              <button
                className="flex w-full items-center gap-1.5 text-left"
                onClick={() => setExpanded(isOpen ? null : item.case_id)}
              >
                <span className="text-[9px] font-medium" style={{ color: theme.global.accent }}>
                  {Math.round(item.similarity * 100)}%
                </span>
                <span className="text-[9px]" style={{ color: theme.global.textPrimary }}>
                  {item.fault_type || '未分類'}
                </span>
                {item.same_turbine && (
                  <span className="rounded px-1 text-[8px]"
                    style={{ backgroundColor: '#22c55e20', color: '#22c55e' }}>
                    同風機
                  </span>
                )}
                <span className="ml-auto text-[8px]" style={{ color: theme.global.textMuted }}>
                  {item.case_id} {isOpen ? '▲' : '▼'}
                </span>
              </button>
              {isOpen && (
                <p className="mt-1 whitespace-pre-wrap text-[9px]"
                  style={{ color: theme.global.textSecondary }}>
                  {item.solution || '（無解法記錄）'}
                </p>
              )}
            </div>
          )
        })}
    </div>
  )
}
