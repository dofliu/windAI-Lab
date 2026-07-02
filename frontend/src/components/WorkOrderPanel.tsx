/**
 * WorkOrderPanel — 工單與派工管理面板。
 *
 * 支援 Tabs 切換：
 * 1. 工單 Kanban 看板 (既存功能)
 * 2. 總監派工面板 (新增功能，支援團隊負載、AI 輔助指派、決策簽核、Markdown 雙向同步)
 */

import { useState, useEffect, useCallback } from 'react'
import { WorkOrder, WorkOrderStatus, WorkOrderPriority, Agent } from '../types/agent'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface WorkOrderPanelProps {
  workOrders: WorkOrder[]
  allAgents?: Agent[]
}

interface TeamLoadSnapshot {
  namespace: string
  wip_count: number
  backlog_count: number
  load_level: string
  suggestion: string
}

interface DailySheet {
  date: string
  hackathon_days_remaining: number
  decision_summary: string
  load_snapshot: TeamLoadSnapshot[]
  ai_advice: {
    bottlenecks: string[]
    risks: string[]
    resource_suggestions: string[]
    schedule_suggestions: string[]
    lessons_learned: string[]
  }
  signed_off: boolean
  markdown_path: string
}

interface Allocation {
  task_id: string
  sheet_date: string
  github_issue: number | null
  title: string
  assignee_agent: string
  collaborators: string[]
  priority: string
  estimated_hours: number
  dependencies: string[]
  deadline: string
  acceptance_criteria: string[]
  rationale: string
  status: string
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

  // ── 新增：分頁與總監派工相關 State ────────────────────────────────
  const [activeTab, setActiveTab] = useState<'kanban' | 'allocation'>('kanban')
  const [loadSnapshot, setLoadSnapshot] = useState<TeamLoadSnapshot[]>([])
  const [dailySheet, setDailySheet] = useState<DailySheet | null>(null)
  const [allocations, setAllocations] = useState<Allocation[]>([])
  
  // AI 建議表單輸入
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDesc, setTaskDesc] = useState('')
  const [taskIssue, setTaskIssue] = useState('')
  const [taskDeps, setTaskDeps] = useState('')
  
  // AI 建議結果
  const [suggestion, setSuggestion] = useState<any | null>(null)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [importMessage, setImportMessage] = useState<string | null>(null)

  // 取得今日日期字串 (YYYY-MM-DD)
  const getTodayDateStr = () => {
    const d = new Date()
    return d.toISOString().split('T')[0]
  }

  const fetchOrders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/work-orders?limit=100`)
      const data = await res.json()
      if (data.work_orders) setOrders(data.work_orders)
    } catch {
      setOrders(wsOrders)
    }
  }, [wsOrders])

  // 載入團隊負載快照
  const fetchLoadSnapshot = async () => {
    try {
      const res = await fetch(`${API_BASE}/director/load-snapshot`)
      if (res.ok) {
        const data = await res.json()
        setLoadSnapshot(data)
      }
    } catch (e) {
      console.error('無法載入負載快照:', e)
    }
  }

  // 載入一日派工單與 allocations
  const fetchDailySheet = async () => {
    const today = getTodayDateStr()
    try {
      const res = await fetch(`${API_BASE}/director/sheets/${today}`)
      if (res.ok) {
        const data = await res.json()
        setDailySheet(data)
        if (data.allocations) {
          setAllocations(data.allocations)
        }
      } else {
        setDailySheet(null)
        setAllocations([])
      }
    } catch (e) {
      console.error('無法載入派工單:', e)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [fetchOrders])

  // 當分頁切換為 總監派工 時，載入數據
  useEffect(() => {
    if (activeTab === 'allocation') {
      fetchLoadSnapshot()
      fetchDailySheet()
    }
  }, [activeTab])

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

  // ── 新增：總監派工相關處理函數 ────────────────────────────────
  const handleUpdateAllocStatus = async (taskId: string, status: string) => {
    try {
      const res = await fetch(`${API_BASE}/director/allocations/${taskId}?status=${status}`, {
        method: 'PATCH',
      })
      if (res.ok) {
        setAllocations(prev => prev.map(a => a.task_id === taskId ? { ...a, status } : a))
      }
    } catch (e) {
      console.error('更新派工狀態失敗:', e)
    }
  }

  const handleSignoff = async () => {
    const today = getTodayDateStr()
    try {
      const res = await fetch(`${API_BASE}/director/sheets/${today}/signoff`, {
        method: 'POST',
      })
      if (res.ok) {
        await fetchDailySheet()
      }
    } catch (e) {
      console.error('簽核失敗:', e)
    }
  }

  const handleGetSuggestion = async () => {
    if (!taskTitle.trim()) return
    setIsSuggesting(true)
    setSuggestion(null)
    try {
      const res = await fetch(`${API_BASE}/director/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: taskTitle.trim(),
          description: taskDesc.trim(),
          github_issue: taskIssue ? intValue(taskIssue) : null,
          dependencies: taskDeps ? taskDeps.split(',').map(d => d.trim()) : [],
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setSuggestion(data)
      }
    } catch (e) {
      console.error('獲取派工建議失敗:', e)
    } finally {
      setIsSuggesting(false)
    }
  }

  const intValue = (val: string) => {
    const num = parseInt(val)
    return isNaN(num) ? null : num
  }

  const handleConfirmAllocation = async () => {
    if (!suggestion) return
    const today = getTodayDateStr()
    
    // 生成 Task ID，格式 WLAB-YYYYMMDD-NN
    // 先算出今日現有 allocation 的數量
    const num = allocations.length + 1
    const padNum = num.toString().padStart(2, '0')
    const taskId = `WLAB-${today.replace(/-/g, '')}-${padNum}`

    const newAlloc = {
      task_id: taskId,
      sheet_date: today,
      github_issue: taskIssue ? intValue(taskIssue) : null,
      title: taskTitle.trim(),
      assignee_agent: suggestion.assignee_agent,
      collaborators: [],
      priority: suggestion.priority,
      estimated_hours: suggestion.estimated_hours,
      dependencies: taskDeps ? taskDeps.split(',').map(d => d.trim()) : [],
      deadline: today, // 預設當天
      acceptance_criteria: ['單元測試通過', '符合 windAI 品質規範'],
      rationale: suggestion.rationale,
      status: 'pending',
    }

    try {
      const res = await fetch(`${API_BASE}/director/allocations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAlloc),
      })
      if (res.ok) {
        // 清空表單與建議
        setTaskTitle('')
        setTaskDesc('')
        setTaskIssue('')
        setTaskDeps('')
        setSuggestion(null)
        
        // 重新整理
        await fetchDailySheet()
        await fetchLoadSnapshot()
      }
    } catch (e) {
      console.error('指派派工失敗:', e)
    }
  }

  const handleImportMarkdown = async () => {
    setIsImporting(true)
    setImportMessage(null)
    try {
      const res = await fetch(`${API_BASE}/director/import-markdown`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        setImportMessage(
          `導入成功！共導入了 ${data.sheets_imported} 份派工單與 ${data.records_imported} 份工作紀錄！`
        )
        if (activeTab === 'allocation') {
          await fetchDailySheet()
          await fetchLoadSnapshot()
        }
      } else {
        setImportMessage('導入失敗，請確認後端日誌。')
      }
    } catch (e) {
      setImportMessage(`導入出錯：${e}`)
    } finally {
      setIsImporting(false)
    }
  }

  const getLoadBadgeStyle = (level: string) => {
    switch (level.toLowerCase()) {
      case 'idle':
        return { backgroundColor: '#22c55e20', color: '#22c55e' }
      case 'low':
        return { backgroundColor: '#3b82f620', color: '#3b82f6' }
      case 'medium':
        return { backgroundColor: '#eab30820', color: '#eab308' }
      case 'high':
        return { backgroundColor: '#f9731620', color: '#f97316' }
      case 'critical':
        return { backgroundColor: '#ef444420', color: '#ef4444' }
      default:
        return { backgroundColor: '#6b728020', color: '#6b7280' }
    }
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
    <div className="space-y-4">
      {/* 分頁 Tab 控制器 */}
      <div className="flex border-b" style={{ borderColor: theme.global.border + '40' }}>
        <button
          onClick={() => setActiveTab('kanban')}
          className="px-4 py-2 text-xs font-semibold border-b-2 transition-all duration-200"
          style={{
            borderColor: activeTab === 'kanban' ? theme.global.accent : 'transparent',
            color: activeTab === 'kanban' ? theme.global.accent : theme.global.textMuted
          }}
        >
          📋 工單 Kanban 看板
        </button>
        <button
          onClick={() => setActiveTab('allocation')}
          className="px-4 py-2 text-xs font-semibold border-b-2 transition-all duration-200"
          style={{
            borderColor: activeTab === 'allocation' ? theme.global.accent : 'transparent',
            color: activeTab === 'allocation' ? theme.global.accent : theme.global.textMuted
          }}
        >
          👑 總監輔助派工面板
        </button>
      </div>

      {/* ── 分頁一：工單看板 ────────────────────────────────────────── */}
      {activeTab === 'kanban' && (
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
      )}

      {/* ── 分頁二：總監輔助派工 ──────────────────────────────────────── */}
      {activeTab === 'allocation' && (
        <div className="space-y-4">
          
          {/* 1. 團隊即時負載快照 */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-semibold" style={{ color: theme.global.textSecondary }}>
              👥 團隊代理負載監控
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
              {loadSnapshot.map(snap => (
                <div key={snap.namespace} className="rounded-lg border p-2 space-y-1" 
                  style={{ borderColor: theme.global.border + '30', backgroundColor: theme.global.panelBg + '50' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold" style={{ color: theme.global.textPrimary }}>{snap.namespace}</span>
                    <span className="rounded px-1.5 py-0.2 text-[7px] font-semibold" style={getLoadBadgeStyle(snap.load_level)}>
                      {snap.load_level.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[9px] space-x-1.5" style={{ color: theme.global.textSecondary }}>
                    <span>WIP: <strong>{snap.wip_count}</strong></span>
                    <span>Backlog: <strong>{snap.backlog_count}</strong></span>
                  </div>
                  <p className="text-[7px] leading-tight" style={{ color: theme.global.textMuted }}>{snap.suggestion}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 2. 今日派工單資訊與簽核 */}
          {dailySheet ? (
            <div className="rounded-lg border p-3 space-y-2.5" 
              style={{ borderColor: theme.global.border + '40', backgroundColor: theme.global.panelBg + '80' }}>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h4 className="text-xs font-bold" style={{ color: theme.global.textPrimary }}>
                    ✍️ 總監今日派工決策書 ({dailySheet.date})
                  </h4>
                  <p className="text-[8px]" style={{ color: theme.global.textMuted }}>
                    Hackathon 倒數剩餘：<strong style={{ color: theme.global.accent }}>{dailySheet.hackathon_days_remaining} 天</strong> | 本機存檔位置：{dailySheet.markdown_path}
                  </p>
                </div>
                {dailySheet.signed_off ? (
                  <span className="rounded px-2 py-0.5 text-[9px] font-bold text-white bg-green-600">
                    已正式簽核核准 ✍️
                  </span>
                ) : (
                  <button
                    onClick={handleSignoff}
                    className="rounded px-2.5 py-1 text-[9px] font-semibold text-white transition-colors hover:brightness-105"
                    style={{ backgroundColor: theme.global.accent }}
                  >
                    簽署發佈本日派工書 ✍️
                  </button>
                )}
              </div>
              
              <div className="rounded p-2 text-[9px]" style={{ backgroundColor: theme.global.pageBg, color: theme.global.textSecondary }}>
                <strong>本日決策摘要：</strong>{dailySheet.decision_summary}
              </div>

              {/* AI Advice 詳情 */}
              <div className="grid grid-cols-2 gap-3 border-t pt-2" style={{ borderColor: theme.global.border + '30' }}>
                <div className="space-y-1">
                  <span className="text-[9px] font-semibold" style={{ color: theme.global.textSecondary }}>⚠️ 潛在瓶頸警告：</span>
                  <ul className="list-disc pl-3 text-[8px]" style={{ color: theme.global.textMuted }}>
                    {dailySheet.ai_advice.bottlenecks.map((b, i) => <li key={i}>{b}</li>)}
                    {dailySheet.ai_advice.bottlenecks.length === 0 && <li>暫無瓶頸。</li>}
                  </ul>
                </div>
                <div className="space-y-1">
                  <span className="text-[9px] font-semibold" style={{ color: theme.global.textSecondary }}>⚡ 風險警示與建議：</span>
                  <ul className="list-disc pl-3 text-[8px]" style={{ color: theme.global.textMuted }}>
                    {dailySheet.ai_advice.risks.map((r, i) => <li key={i}>{r}</li>)}
                    {dailySheet.ai_advice.risks.length === 0 && <li>暫無特別風險。</li>}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-4 text-center text-[10px]" 
              style={{ borderColor: theme.global.border, color: theme.global.textMuted }}>
              📅 今日暫未指派任何任務。在下方「AI 輔助指派」創建首筆派工將自動生成派工決策書。
            </div>
          )}

          {/* 3. 今日已派工任務列表 (表格) */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-semibold" style={{ color: theme.global.textSecondary }}>
              📋 本日任務分配明細
            </h4>
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: theme.global.border + '40' }}>
              <table className="w-full text-left border-collapse text-[10px]">
                <thead>
                  <tr style={{ backgroundColor: theme.global.panelBg + '80', color: theme.global.textSecondary }}>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>任務 ID</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>GitHub</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>任務標題</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>指派代理</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>優先級</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>預估工時</th>
                    <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>狀態設定</th>
                  </tr>
                </thead>
                <tbody>
                  {allocations.map(alloc => (
                    <tr key={alloc.task_id} style={{ color: theme.global.textPrimary }}>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>{alloc.task_id}</td>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                        {alloc.github_issue ? `#${alloc.github_issue}` : '無'}
                      </td>
                      <td className="p-2 border-b font-medium" style={{ borderColor: theme.global.border + '40' }}>{alloc.title}</td>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>{alloc.assignee_agent}</td>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                        <span className="rounded px-1.5 py-0.5 text-[8px]" 
                          style={{ 
                            backgroundColor: alloc.priority === 'P1' ? '#ef444420' : '#3b82f620',
                            color: alloc.priority === 'P1' ? '#ef4444' : '#3b82f6' 
                          }}>
                          {alloc.priority}
                        </span>
                      </td>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>{alloc.estimated_hours} 小時</td>
                      <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                        <select
                          value={alloc.status}
                          onChange={e => handleUpdateAllocStatus(alloc.task_id, e.target.value)}
                          className="rounded border px-1 py-0.5 text-[9px] outline-none"
                          style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                        >
                          <option value="pending">PENDING</option>
                          <option value="in_progress">IN_PROGRESS</option>
                          <option value="blocked">BLOCKED</option>
                          <option value="completed">COMPLETED</option>
                          <option value="cancelled">CANCELLED</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                  {allocations.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-4 text-center text-muted" style={{ color: theme.global.textMuted }}>
                        今日尚無已指派任務
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* 4. AI 輔助指派生成器 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t pt-3" style={{ borderColor: theme.global.border + '40' }}>
            {/* 表單輸入 */}
            <div className="rounded-lg border p-3 space-y-2.5" 
              style={{ borderColor: theme.global.border + '30', backgroundColor: theme.global.panelBg + '30' }}>
              <h4 className="text-xs font-semibold mb-1" style={{ color: theme.global.textPrimary }}>
                🤖 AI 輔助派工規劃
              </h4>
              <div className="space-y-1">
                <span className="text-[8px]" style={{ color: theme.global.textMuted }}>任務標題：</span>
                <input
                  value={taskTitle}
                  onChange={e => setTaskTitle(e.target.value)}
                  placeholder="請輸入任務名稱，如：修復 CSV 讀取註解問題"
                  className="w-full rounded border px-2 py-1 text-xs outline-none"
                  style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}
                />
              </div>
              <div className="space-y-1">
                <span className="text-[8px]" style={{ color: theme.global.textMuted }}>任務描述：</span>
                <textarea
                  value={taskDesc}
                  onChange={e => setTaskDesc(e.target.value)}
                  placeholder="請輸入任務詳細背景與需要完成的工作細節"
                  rows={2}
                  className="w-full rounded border px-2 py-1 text-xs outline-none resize-none"
                  style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <span className="text-[8px]" style={{ color: theme.global.textMuted }}>GitHub Issue：</span>
                  <input
                    value={taskIssue}
                    onChange={e => setTaskIssue(e.target.value)}
                    placeholder="例如：42 (選填)"
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}
                  />
                </div>
                <div className="space-y-0.5">
                  <span className="text-[8px]" style={{ color: theme.global.textMuted }}>前置任務依賴：</span>
                  <input
                    value={taskDeps}
                    onChange={e => setTaskDeps(e.target.value)}
                    placeholder="WLAB-YYYYMMDD-NN"
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg, color: theme.global.textPrimary }}
                  />
                </div>
              </div>
              <button
                onClick={handleGetSuggestion}
                disabled={!taskTitle.trim() || isSuggesting}
                className="w-full rounded py-1.5 text-xs font-semibold text-white disabled:opacity-40 transition-opacity"
                style={{ backgroundColor: theme.global.accent }}
              >
                {isSuggesting ? 'AI 規劃中...' : '生成派工指派建議 💡'}
              </button>
            </div>

            {/* AI 建議結果展示 */}
            <div className="rounded-lg border p-3 flex flex-col justify-between" 
              style={{ borderColor: theme.global.border + '30', backgroundColor: theme.global.panelBg + '30' }}>
              <div className="space-y-2">
                <h4 className="text-xs font-semibold" style={{ color: theme.global.textPrimary }}>
                  💡 智慧推薦結果
                </h4>
                {suggestion ? (
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <div className="flex-1 rounded p-2 text-center" style={{ backgroundColor: theme.global.pageBg }}>
                        <span className="text-[8px] block" style={{ color: theme.global.textMuted }}>指派代理</span>
                        <strong className="text-xs" style={{ color: theme.global.accent }}>{suggestion.assignee_agent}</strong>
                      </div>
                      <div className="flex-1 rounded p-2 text-center" style={{ backgroundColor: theme.global.pageBg }}>
                        <span className="text-[8px] block" style={{ color: theme.global.textMuted }}>優先級建議</span>
                        <strong className="text-xs" style={{ color: '#f97316' }}>{suggestion.priority}</strong>
                      </div>
                      <div className="flex-1 rounded p-2 text-center" style={{ backgroundColor: theme.global.pageBg }}>
                        <span className="text-[8px] block" style={{ color: theme.global.textMuted }}>預估工時</span>
                        <strong className="text-xs" style={{ color: theme.global.textPrimary }}>{suggestion.estimated_hours}h</strong>
                      </div>
                    </div>
                    
                    <div className="text-[9px]" style={{ color: theme.global.textSecondary }}>
                      <strong>指派理由：</strong>{suggestion.rationale}
                    </div>

                    {suggestion.risk_flags.length > 0 && (
                      <div className="rounded border p-1.5 text-[8px]" 
                        style={{ borderColor: '#ef444430', backgroundColor: '#ef444408', color: '#ef4444' }}>
                        <strong>⚠️ 風險標記：</strong>
                        <ul className="list-disc pl-3">
                          {suggestion.risk_flags.map((rf: string, idx: number) => <li key={idx}>{rf}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-28 flex items-center justify-center text-[10px]" style={{ color: theme.global.textMuted }}>
                    請填寫左側表單並點擊「生成派工指派建議」
                  </div>
                )}
              </div>
              
              {suggestion && (
                <button
                  onClick={handleConfirmAllocation}
                  className="w-full rounded py-1.5 text-xs font-semibold text-white bg-green-600 transition-colors hover:bg-green-700"
                >
                  確認指派，寫入庫與 Markdown 檔案 🚀
                </button>
              )}
            </div>
          </div>

          {/* 5. 歷史工作紀錄一鍵匯入與工具 */}
          <div className="rounded-lg border p-3 flex items-center justify-between mt-3" 
            style={{ borderColor: theme.global.border + '30', backgroundColor: theme.global.panelBg + '10' }}>
            <div className="space-y-0.5">
              <span className="text-[10px] font-bold block" style={{ color: theme.global.textPrimary }}>
                📂 一鍵匯入與同步工具
              </span>
              <span className="text-[8px]" style={{ color: theme.global.textMuted }}>
                將 windAI-Lab 硬碟中既有的 YYYY-MM-DD-allocation.md 及 WLAB-*.md 匯入 SQLite
              </span>
            </div>
            <button
              onClick={handleImportMarkdown}
              disabled={isImporting}
              className="rounded border px-3 py-1.5 text-[10px] font-semibold transition-colors hover:brightness-105"
              style={{ borderColor: theme.global.border, color: theme.global.textPrimary }}
            >
              {isImporting ? '匯入中...' : '匯入歷史 Markdown 檔'}
            </button>
          </div>
          
          {importMessage && (
            <div className="rounded p-2 text-[10px]" 
              style={{ backgroundColor: theme.global.accent + '10', color: theme.global.textPrimary }}>
              📢 {importMessage}
            </div>
          )}

        </div>
      )}
    </div>
  )
}
