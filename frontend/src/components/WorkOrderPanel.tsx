/**
 * WorkOrderPanel — 工單管理面板。
 *
 * 以 Kanban 看板形式顯示工單，支援建立、更新狀態、
 * 指派代理與新增備註。
 */

import { useState, useEffect, useCallback } from 'react'
import { WorkOrder, WorkOrderStatus, WorkOrderPriority, Agent } from '../types/agent'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface WorkOrderPanelProps {
  workOrders: WorkOrder[]
  allAgents?: Agent[]
}

const PRIORITY_CONFIG: Record<WorkOrderPriority, { label: string; color: string; icon: string }> = {
  critical: { label: '緊急', color: '#ef4444', icon: '🔴' },
  high: { label: '高', color: '#f97316', icon: '🟠' },
  medium: { label: '中', color: '#eab308', icon: '🟡' },
  low: { label: '低', color: '#6b7280', icon: '⚪' },
}

const STATUS_COLUMNS: { status: WorkOrderStatus; label: string; icon: string }[] = [
  { status: 'open', label: '待處理', icon: '📋' },
  { status: 'in_progress', label: '進行中', icon: '🔧' },
  { status: 'completed', label: '已完成', icon: '✅' },
]

export default function WorkOrderPanel({ workOrders: wsOrders, allAgents = [] }: WorkOrderPanelProps) {
  const { theme } = useTheme()
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [noteText, setNoteText] = useState('')

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/work-orders?limit=100`)
      const data = await res.json()
      if (data.work_orders) setOrders(data.work_orders)
    } catch {
      setOrders(wsOrders)
    }
  }, [wsOrders])

  useEffect(() => { fetchOrders() }, [fetchOrders])

  // WebSocket 即時更新
  useEffect(() => {
    if (wsOrders.length > 0) {
      setOrders(prev => {
        const map = new Map(prev.map(o => [o.id, o]))
        wsOrders.forEach(o => map.set(o.id, o))
        return Array.from(map.values()).sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        )
      })
    }
  }, [wsOrders])

  const handleUpdateStatus = async (orderId: string, status: WorkOrderStatus) => {
    try {
      const res = await fetch(`${API_BASE}/work-orders/${orderId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (res.ok) {
        const data = await res.json()
        setOrders(prev => prev.map(o => o.id === orderId ? data.work_order : o))
      }
    } catch { /* 離線模式 */ }
  }

  const handleAddNote = async (orderId: string) => {
    if (!noteText.trim()) return
    try {
      const res = await fetch(`${API_BASE}/work-orders/${orderId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ author: 'user', text: noteText.trim() }),
      })
      if (res.ok) {
        const data = await res.json()
        setOrders(prev => prev.map(o => o.id === orderId ? data.work_order : o))
        setNoteText('')
      }
    } catch { /* 離線模式 */ }
  }

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    try {
      await fetch(`${API_BASE}/work-orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: form.get('title'),
          description: form.get('description') || '',
          priority: form.get('priority'),
          turbine_id: form.get('turbine_id') || null,
        }),
      })
      setShowCreateForm(false)
      await fetchOrders()
    } catch { /* 離線模式 */ }
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('zh-TW', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  }

  const detail = selectedOrder ? orders.find(o => o.id === selectedOrder) : null

  const agentName = (id: string) => {
    const agent = allAgents.find(a => a.id === id)
    return agent?.displayName ?? id
  }

  return (
    <div className="space-y-3">
      {/* 標題 + 操作 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
          工單管理
        </h3>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-colors hover:brightness-110"
          style={{ borderColor: theme.global.border, color: theme.global.accent }}
        >
          + 新增工單
        </button>
      </div>

      {/* 建立表單 */}
      {showCreateForm && (
        <form
          onSubmit={handleCreate}
          className="rounded-lg border p-3 space-y-2"
          style={{ borderColor: theme.global.accent + '40', backgroundColor: theme.global.accent + '08' }}
        >
          <div className="grid grid-cols-3 gap-2">
            <input name="title" required placeholder="工單標題"
              className="col-span-2 rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }} />
            <select name="priority" defaultValue="medium"
              className="rounded border px-2 py-1 text-xs outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}>
              <option value="critical">緊急</option>
              <option value="high">高</option>
              <option value="medium">中</option>
              <option value="low">低</option>
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
            <button type="submit"
              className="rounded px-3 py-1 text-[10px] font-medium text-white"
              style={{ backgroundColor: theme.global.accent }}>
              建立
            </button>
          </div>
        </form>
      )}

      {/* Kanban 看板 */}
      <div className="grid grid-cols-3 gap-2" style={{ minHeight: 200 }}>
        {STATUS_COLUMNS.map(col => {
          const colOrders = orders.filter(o => o.status === col.status)
          return (
            <div key={col.status} className="space-y-1.5">
              {/* 欄標題 */}
              <div className="flex items-center gap-1.5 px-1 pb-1 border-b"
                style={{ borderColor: theme.global.border + '40' }}>
                <span className="text-xs">{col.icon}</span>
                <span className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>
                  {col.label}
                </span>
                <span className="rounded-full px-1.5 py-0.5 text-[8px]"
                  style={{ backgroundColor: theme.global.border + '60', color: theme.global.textMuted }}>
                  {colOrders.length}
                </span>
              </div>

              {/* 工單卡片 */}
              {colOrders.map(order => {
                const pri = PRIORITY_CONFIG[order.priority]
                const isSelected = selectedOrder === order.id
                return (
                  <button
                    key={order.id}
                    onClick={() => setSelectedOrder(isSelected ? null : order.id)}
                    className="w-full rounded-lg border p-2 text-left transition-all hover:brightness-105"
                    style={{
                      borderColor: isSelected ? theme.global.accent + '60' : theme.global.border + '40',
                      backgroundColor: isSelected ? theme.global.accent + '08' : theme.global.panelBg + '60',
                    }}
                  >
                    <div className="flex items-center gap-1 mb-0.5">
                      <span className="text-[8px]">{pri.icon}</span>
                      <span className="text-[10px] font-medium truncate"
                        style={{ color: theme.global.textPrimary }}>
                        {order.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {order.turbine_id && (
                        <span className="text-[8px]" style={{ color: theme.global.textMuted }}>
                          {order.turbine_id}
                        </span>
                      )}
                      <span className="text-[8px]" style={{ color: theme.global.textMuted }}>
                        {formatTime(order.created_at)}
                      </span>
                    </div>
                    {order.assigned_agents.length > 0 && (
                      <div className="flex gap-0.5 mt-1 flex-wrap">
                        {order.assigned_agents.map(id => (
                          <span key={id} className="rounded px-1 py-0.5 text-[7px]"
                            style={{ backgroundColor: theme.global.border + '60', color: theme.global.textSecondary }}>
                            {agentName(id)}
                          </span>
                        ))}
                      </div>
                    )}
                  </button>
                )
              })}

              {colOrders.length === 0 && (
                <div className="py-4 text-center text-[9px]" style={{ color: theme.global.textMuted }}>
                  無工單
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* 工單詳情面板 */}
      {detail && (
        <div className="rounded-lg border p-3 space-y-2"
          style={{ borderColor: theme.global.accent + '30', backgroundColor: theme.global.panelBg + '80' }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium" style={{ color: theme.global.textPrimary }}>
                {detail.title}
              </span>
              <span className="rounded px-1.5 py-0.5 text-[8px]"
                style={{ backgroundColor: PRIORITY_CONFIG[detail.priority].color + '20', color: PRIORITY_CONFIG[detail.priority].color }}>
                {PRIORITY_CONFIG[detail.priority].label}
              </span>
            </div>
            <span className="text-[9px]" style={{ color: theme.global.textMuted }}>
              {detail.id}
            </span>
          </div>

          {detail.description && (
            <p className="text-[10px]" style={{ color: theme.global.textSecondary }}>
              {detail.description}
            </p>
          )}

          {detail.alert_id && (
            <div className="text-[9px]" style={{ color: theme.global.textMuted }}>
              關聯告警：{detail.alert_id}
            </div>
          )}

          {/* 狀態操作 */}
          <div className="flex items-center gap-1.5">
            <span className="text-[9px]" style={{ color: theme.global.textMuted }}>狀態操作：</span>
            {detail.status === 'open' && (
              <button onClick={() => handleUpdateStatus(detail.id, 'in_progress')}
                className="rounded px-2 py-0.5 text-[9px] font-medium"
                style={{ backgroundColor: '#3b82f620', color: '#3b82f6' }}>
                開始處理
              </button>
            )}
            {detail.status === 'in_progress' && (
              <button onClick={() => handleUpdateStatus(detail.id, 'completed')}
                className="rounded px-2 py-0.5 text-[9px] font-medium"
                style={{ backgroundColor: '#22c55e20', color: '#22c55e' }}>
                標記完成
              </button>
            )}
            {(detail.status === 'open' || detail.status === 'in_progress') && (
              <button onClick={() => handleUpdateStatus(detail.id, 'cancelled')}
                className="rounded px-2 py-0.5 text-[9px]"
                style={{ color: theme.global.textMuted }}>
                取消工單
              </button>
            )}
          </div>

          {/* 備註時間線 */}
          {detail.notes.length > 0 && (
            <div className="space-y-1 border-t pt-2" style={{ borderColor: theme.global.border + '40' }}>
              <span className="text-[9px] font-medium" style={{ color: theme.global.textSecondary }}>備註</span>
              {detail.notes.map((note, i) => (
                <div key={i} className="flex items-start gap-1.5">
                  <span className="text-[8px] shrink-0 mt-0.5" style={{ color: theme.global.textMuted }}>
                    {formatTime(note.timestamp)}
                  </span>
                  <span className="text-[8px] shrink-0 font-medium" style={{ color: theme.global.accent }}>
                    {note.author}
                  </span>
                  <span className="text-[9px]" style={{ color: theme.global.textSecondary }}>
                    {note.text}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* 新增備註 */}
          <div className="flex items-center gap-1.5">
            <input
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              placeholder="新增備註..."
              className="flex-1 rounded border px-2 py-1 text-[10px] outline-none"
              style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
              onKeyDown={e => { if (e.key === 'Enter') handleAddNote(detail.id) }}
            />
            <button onClick={() => handleAddNote(detail.id)}
              disabled={!noteText.trim()}
              className="rounded px-2 py-1 text-[9px] font-medium text-white disabled:opacity-40"
              style={{ backgroundColor: theme.global.accent }}>
              送出
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
