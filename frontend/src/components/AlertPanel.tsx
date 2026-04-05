/**
 * AlertPanel — 告警管理面板。
 *
 * 顯示告警列表、支援篩選、確認/解決/駁回操作，
 * 以及從告警建立工單的快捷功能。
 */

import { useState, useEffect, useCallback } from 'react'
import { Alert, AlertSeverity, AlertStatus } from '../types/agent'
import { useTheme } from '../themes'

interface AlertPanelProps {
  alerts: Alert[]
  onAlertsChange?: (alerts: Alert[]) => void
}

const SEVERITY_CONFIG: Record<AlertSeverity, { label: string; icon: string; color: string }> = {
  critical: { label: '嚴重', icon: '🔴', color: '#ef4444' },
  warning: { label: '警告', icon: '🟡', color: '#f59e0b' },
  info: { label: '資訊', icon: '🔵', color: '#3b82f6' },
}

const STATUS_CONFIG: Record<AlertStatus, { label: string; icon: string }> = {
  active: { label: '待處理', icon: '⚠️' },
  acknowledged: { label: '已確認', icon: '👁️' },
  resolved: { label: '已解決', icon: '✅' },
  dismissed: { label: '已駁回', icon: '🚫' },
}

export default function AlertPanel({ alerts: wsAlerts, onAlertsChange }: AlertPanelProps) {
  const { theme } = useTheme()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [filterSeverity, setFilterSeverity] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('active')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [creating, setCreating] = useState(false)

  // 從 API 載入 + 合併 WebSocket 即時資料
  const fetchAlerts = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (filterStatus !== 'all') params.set('status', filterStatus)
      if (filterSeverity !== 'all') params.set('severity', filterSeverity)
      const res = await fetch(`http://localhost:8000/api/alerts?${params}`)
      const data = await res.json()
      if (data.alerts) setAlerts(data.alerts)
    } catch {
      // 後端不可用時使用 WebSocket 資料
      setAlerts(wsAlerts)
    }
  }, [filterStatus, filterSeverity, wsAlerts])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])

  // WebSocket 即時更新
  useEffect(() => {
    if (wsAlerts.length > 0) {
      setAlerts(prev => {
        const map = new Map(prev.map(a => [a.id, a]))
        wsAlerts.forEach(a => map.set(a.id, a))
        return Array.from(map.values()).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      })
    }
  }, [wsAlerts])

  const handleUpdateStatus = async (alertId: string, status: AlertStatus) => {
    try {
      const res = await fetch(`http://localhost:8000/api/alerts/${alertId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status, resolved_by: 'user' }),
      })
      if (res.ok) {
        const data = await res.json()
        setAlerts(prev => prev.map(a => a.id === alertId ? data.alert : a))
        if (onAlertsChange) {
          onAlertsChange(alerts.map(a => a.id === alertId ? data.alert : a))
        }
      }
    } catch { /* 離線模式 */ }
  }

  const handleCreateWorkOrder = async (alertId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/alerts/${alertId}/create-work-order`, {
        method: 'POST',
      })
      if (res.ok) {
        await fetchAlerts()
      }
    } catch { /* 離線模式 */ }
  }

  const handleCreateAlert = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setCreating(true)
    const form = new FormData(e.currentTarget)
    try {
      await fetch('http://localhost:8000/api/alerts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turbine_id: form.get('turbine_id') || null,
          severity: form.get('severity'),
          title: form.get('title'),
          description: form.get('description') || '',
          tags: [],
        }),
      })
      setShowCreateForm(false)
      await fetchAlerts()
    } catch { /* 離線模式 */ }
    setCreating(false)
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('zh-TW', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  const activeCount = alerts.filter(a => a.status === 'active').length
  const criticalCount = alerts.filter(a => a.severity === 'critical' && a.status === 'active').length

  return (
    <div className="space-y-3">
      {/* 統計列 + 操作列 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
            告警列表
          </h3>
          {criticalCount > 0 && (
            <span className="rounded-full px-2 py-0.5 text-[10px] font-medium animate-pulse"
              style={{ backgroundColor: '#ef444430', color: '#ef4444' }}>
              {criticalCount} 嚴重
            </span>
          )}
          {activeCount > 0 && (
            <span className="rounded-full px-2 py-0.5 text-[10px]"
              style={{ backgroundColor: '#f59e0b30', color: '#f59e0b' }}>
              {activeCount} 待處理
            </span>
          )}
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors hover:brightness-110"
          style={{ borderColor: theme.global.border, color: theme.global.accent }}
        >
          + 手動建立
        </button>
      </div>

      {/* 手動建立表單 */}
      {showCreateForm && (
        <form
          onSubmit={handleCreateAlert}
          className="rounded-lg border p-3 space-y-2"
          style={{ borderColor: theme.global.accent + '40', backgroundColor: theme.global.accent + '08' }}
        >
          <div className="grid grid-cols-3 gap-2">
            <input name="title" required placeholder="告警標題"
              className="col-span-2 rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }} />
            <select name="severity" defaultValue="warning"
              className="rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}>
              <option value="critical">嚴重</option>
              <option value="warning">警告</option>
              <option value="info">資訊</option>
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input name="turbine_id" placeholder="風機 ID（選填）"
              className="rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }} />
            <input name="description" placeholder="詳細描述（選填）"
              className="col-span-2 rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }} />
          </div>
          <div className="flex gap-2 justify-end">
            <button type="button" onClick={() => setShowCreateForm(false)}
              className="rounded px-3 py-1 text-[10px]" style={{ color: theme.global.textMuted }}>
              取消
            </button>
            <button type="submit" disabled={creating}
              className="rounded px-3 py-1 text-[10px] font-medium text-white disabled:opacity-40"
              style={{ backgroundColor: theme.global.accent }}>
              建立
            </button>
          </div>
        </form>
      )}

      {/* 篩選列 */}
      <div className="flex items-center gap-2">
        <span className="text-[9px]" style={{ color: theme.global.textMuted }}>篩選：</span>
        {['all', 'active', 'acknowledged', 'resolved'].map(s => (
          <button key={s} onClick={() => setFilterStatus(s)}
            className="rounded px-2 py-0.5 text-[10px] transition-colors"
            style={{
              backgroundColor: filterStatus === s ? theme.global.accent + '20' : 'transparent',
              color: filterStatus === s ? theme.global.accent : theme.global.textMuted,
            }}>
            {s === 'all' ? '全部' : STATUS_CONFIG[s as AlertStatus]?.label ?? s}
          </button>
        ))}
        <div className="mx-1 h-3 w-px" style={{ backgroundColor: theme.global.border }} />
        {['all', 'critical', 'warning', 'info'].map(s => (
          <button key={s} onClick={() => setFilterSeverity(s)}
            className="rounded px-2 py-0.5 text-[10px] transition-colors"
            style={{
              backgroundColor: filterSeverity === s ? (SEVERITY_CONFIG[s as AlertSeverity]?.color ?? theme.global.accent) + '20' : 'transparent',
              color: filterSeverity === s ? (SEVERITY_CONFIG[s as AlertSeverity]?.color ?? theme.global.accent) : theme.global.textMuted,
            }}>
            {s === 'all' ? '全部' : SEVERITY_CONFIG[s as AlertSeverity]?.label ?? s}
          </button>
        ))}
      </div>

      {/* 告警列表 */}
      <div className="space-y-1.5">
        {alerts.length === 0 && (
          <div className="py-8 text-center text-xs" style={{ color: theme.global.textMuted }}>
            目前沒有符合條件的告警
          </div>
        )}
        {alerts.map(alert => {
          const sev = SEVERITY_CONFIG[alert.severity]
          const st = STATUS_CONFIG[alert.status]
          return (
            <div
              key={alert.id}
              className="flex items-start gap-2 rounded-lg border p-2.5 transition-colors"
              style={{
                borderColor: alert.status === 'active' ? sev.color + '40' : theme.global.border + '40',
                backgroundColor: alert.status === 'active' ? sev.color + '06' : 'transparent',
              }}
            >
              {/* 嚴重程度圖示 */}
              <span className="text-sm mt-0.5 shrink-0">{sev.icon}</span>

              {/* 內容 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium truncate" style={{ color: theme.global.textPrimary }}>
                    {alert.title}
                  </span>
                  <span className="shrink-0 rounded px-1.5 py-0.5 text-[8px]"
                    style={{ backgroundColor: sev.color + '20', color: sev.color }}>
                    {sev.label}
                  </span>
                  <span className="shrink-0 rounded px-1.5 py-0.5 text-[8px]"
                    style={{ backgroundColor: theme.global.border + '60', color: theme.global.textMuted }}>
                    {st.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {alert.turbine_id && (
                    <span className="text-[9px]" style={{ color: theme.global.textSecondary }}>
                      {alert.turbine_id}
                    </span>
                  )}
                  {alert.source_system && (
                    <span className="text-[9px]" style={{ color: theme.global.textMuted }}>
                      via {alert.source_system}
                    </span>
                  )}
                  <span className="text-[9px]" style={{ color: theme.global.textMuted }}>
                    {formatTime(alert.occurred_at || alert.created_at)}
                  </span>
                  {alert.work_order_id && (
                    <span className="text-[9px] rounded px-1 py-0.5"
                      style={{ backgroundColor: theme.global.accent + '15', color: theme.global.accent }}>
                      工單 {alert.work_order_id}
                    </span>
                  )}
                </div>
                {alert.description && (
                  <p className="text-[10px] mt-0.5 line-clamp-2" style={{ color: theme.global.textMuted }}>
                    {alert.description}
                  </p>
                )}
              </div>

              {/* 操作按鈕 */}
              <div className="flex items-center gap-1 shrink-0">
                {alert.status === 'active' && (
                  <>
                    <button onClick={() => handleUpdateStatus(alert.id, 'acknowledged')}
                      className="rounded px-1.5 py-0.5 text-[9px] transition-colors hover:brightness-110"
                      style={{ backgroundColor: theme.global.border + '40', color: theme.global.textSecondary }}
                      title="確認告警">
                      確認
                    </button>
                    <button onClick={() => handleUpdateStatus(alert.id, 'resolved')}
                      className="rounded px-1.5 py-0.5 text-[9px] transition-colors hover:brightness-110"
                      style={{ backgroundColor: '#22c55e20', color: '#22c55e' }}
                      title="標記已解決">
                      解決
                    </button>
                  </>
                )}
                {alert.status === 'acknowledged' && (
                  <button onClick={() => handleUpdateStatus(alert.id, 'resolved')}
                    className="rounded px-1.5 py-0.5 text-[9px] transition-colors hover:brightness-110"
                    style={{ backgroundColor: '#22c55e20', color: '#22c55e' }}>
                    解決
                  </button>
                )}
                {(alert.status === 'active' || alert.status === 'acknowledged') && !alert.work_order_id && (
                  <button onClick={() => handleCreateWorkOrder(alert.id)}
                    className="rounded px-1.5 py-0.5 text-[9px] transition-colors hover:brightness-110"
                    style={{ backgroundColor: theme.global.accent + '20', color: theme.global.accent }}
                    title="從此告警建立工單">
                    建工單
                  </button>
                )}
                {alert.status === 'active' && (
                  <button onClick={() => handleUpdateStatus(alert.id, 'dismissed')}
                    className="rounded px-1.5 py-0.5 text-[9px] transition-colors hover:brightness-110"
                    style={{ color: theme.global.textMuted }}
                    title="駁回告警">
                    駁回
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
