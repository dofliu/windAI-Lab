/**
 * WindFarmPanel — 風場運維管理面板。
 *
 * 顯示所有客戶風場的健康狀態、監控摘要、工單列表。
 * 支援註冊新風場、手動觸發檢查、查看歷史。
 */

import { useState, useEffect, useCallback } from 'react'
import { useTheme } from '../themes'

interface WindFarm {
  id: string
  name: string
  location: string
  turbine_count: number
  rated_power_mw: number
  status: string
  poll_interval_min: number
  auto_diagnose: boolean
  last_health_check_at: string
  turbines: Record<string, TurbineStatus>
  tags: string[]
}

interface TurbineStatus {
  turbine_id: string
  health_score: number
  health_level: string
  last_check_at: string
  anomaly_count: number
  active_ticket_id?: string
}

interface ServiceTicket {
  id: string
  wind_farm_name: string
  turbine_id: string
  title: string
  priority: string
  status: string
  trigger: string
  health_score_at_creation?: number
  created_at: string
}

interface MonitorSummary {
  running: boolean
  total_farms: number
  active_farms: number
  total_turbines: number
  monitored_turbines: number
  total_capacity_mw: number
  open_tickets: number
  health_distribution: Record<string, number>
}

const API = 'http://localhost:8000/api'

export default function WindFarmPanel() {
  const { theme } = useTheme()
  const [farms, setFarms] = useState<WindFarm[]>([])
  const [tickets, setTickets] = useState<ServiceTicket[]>([])
  const [summary, setSummary] = useState<MonitorSummary | null>(null)
  const [selectedFarm, setSelectedFarm] = useState<string | null>(null)
  const [showRegister, setShowRegister] = useState(false)
  const [tab, setTab] = useState<'overview' | 'tickets'>('overview')

  const fetchAll = useCallback(async () => {
    try {
      const [farmsRes, ticketsRes, summaryRes] = await Promise.all([
        fetch(`${API}/wind-farms`),
        fetch(`${API}/tickets?status=open`),
        fetch(`${API}/monitor/status`),
      ])
      if (farmsRes.ok) setFarms(await farmsRes.json())
      if (ticketsRes.ok) setTickets(await ticketsRes.json())
      if (summaryRes.ok) setSummary(await summaryRes.json())
    } catch { /* backend offline */ }
  }, [])

  useEffect(() => {
    fetchAll()
    const timer = setInterval(fetchAll, 15000)
    return () => clearInterval(timer)
  }, [fetchAll])

  const handleCheckNow = async (farmId: string) => {
    await fetch(`${API}/wind-farms/${farmId}/check-now`, { method: 'POST' })
    setTimeout(fetchAll, 2000)
  }

  const handleRegister = async (data: Record<string, string | number | boolean>) => {
    await fetch(`${API}/wind-farms/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    setShowRegister(false)
    fetchAll()
  }

  const priorityColor = (p: string) => {
    const map: Record<string, string> = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#6b7280' }
    return map[p] || theme.global.textMuted
  }

  const statusBadge = (s: string) => {
    const map: Record<string, { bg: string; fg: string; label: string }> = {
      active: { bg: '#22c55e20', fg: '#22c55e', label: '監控中' },
      paused: { bg: '#eab30820', fg: '#eab308', label: '已暫停' },
      error: { bg: '#ef444420', fg: '#ef4444', label: '異常' },
      onboarding: { bg: '#6366f120', fg: '#6366f1', label: '上線中' },
    }
    const m = map[s] || map.onboarding
    return (
      <span className="rounded-full px-2 py-0.5 text-[9px] font-medium" style={{ backgroundColor: m.bg, color: m.fg }}>
        {m.label}
      </span>
    )
  }

  const healthIcon = (level: string) => {
    const map: Record<string, string> = { healthy: '🟢', warning: '🟡', critical: '🔴', unknown: '⚪' }
    return map[level] || '⚪'
  }

  const detail = farms.find((f) => f.id === selectedFarm)

  return (
    <div className="flex h-full flex-col overflow-hidden" style={{ color: theme.global.textPrimary }}>
      {/* ── 頂部摘要 ── */}
      {summary && (
        <div className="flex items-center gap-4 border-b px-4 py-2" style={{ borderColor: theme.global.border }}>
          <div className="flex items-center gap-1.5">
            <span className="text-lg">🏢</span>
            <div>
              <div className="text-[10px]" style={{ color: theme.global.textMuted }}>客戶風場</div>
              <div className="text-sm font-bold">{summary.total_farms}</div>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-lg">🌬️</span>
            <div>
              <div className="text-[10px]" style={{ color: theme.global.textMuted }}>總風機</div>
              <div className="text-sm font-bold">{summary.total_turbines}</div>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-lg">⚡</span>
            <div>
              <div className="text-[10px]" style={{ color: theme.global.textMuted }}>總容量</div>
              <div className="text-sm font-bold">{summary.total_capacity_mw} MW</div>
            </div>
          </div>
          {summary.health_distribution && (
            <div className="flex items-center gap-2 ml-auto text-[10px]">
              <span>🟢 {summary.health_distribution.healthy || 0}</span>
              <span>🟡 {summary.health_distribution.warning || 0}</span>
              <span>🔴 {summary.health_distribution.critical || 0}</span>
            </div>
          )}
          {summary.open_tickets > 0 && (
            <span className="rounded-full px-2 py-0.5 text-[9px] font-medium" style={{ backgroundColor: '#ef444420', color: '#ef4444' }}>
              {summary.open_tickets} 件待處理工單
            </span>
          )}
        </div>
      )}

      {/* ── Tab 切換 ── */}
      <div className="flex border-b px-4" style={{ borderColor: theme.global.border }}>
        {(['overview', 'tickets'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="px-3 py-1.5 text-xs font-medium border-b-2 transition-colors"
            style={{
              borderColor: tab === t ? theme.global.accent : 'transparent',
              color: tab === t ? theme.global.accent : theme.global.textMuted,
            }}
          >
            {t === 'overview' ? '風場總覽' : `工單 (${tickets.length})`}
          </button>
        ))}
        <button
          onClick={() => setShowRegister(!showRegister)}
          className="ml-auto px-2 py-1 text-[10px] rounded hover:brightness-125"
          style={{ color: theme.global.accent }}
        >
          + 新增風場
        </button>
      </div>

      {/* ── 新增風場表單 ── */}
      {showRegister && (
        <RegisterForm theme={theme} onSubmit={handleRegister} onCancel={() => setShowRegister(false)} />
      )}

      {/* ── 風場總覽 ── */}
      {tab === 'overview' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {farms.length === 0 && (
            <div className="text-center py-12 text-xs" style={{ color: theme.global.textMuted }}>
              尚無風場客戶。點擊「+ 新增風場」開始。
            </div>
          )}
          {farms.map((farm) => (
            <div
              key={farm.id}
              className="rounded-lg border p-3 cursor-pointer hover:brightness-110 transition-all"
              style={{ borderColor: selectedFarm === farm.id ? theme.global.accent : theme.global.border, backgroundColor: theme.global.surfaceAlt || theme.global.surface }}
              onClick={() => setSelectedFarm(selectedFarm === farm.id ? null : farm.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-base">🏗️</span>
                  <div>
                    <div className="text-xs font-semibold">{farm.name}</div>
                    <div className="text-[10px]" style={{ color: theme.global.textMuted }}>
                      {farm.location || '未設定位置'} · {farm.turbine_count} 台 · {farm.rated_power_mw} MW
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {statusBadge(farm.status)}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleCheckNow(farm.id) }}
                    className="rounded px-2 py-0.5 text-[9px] border hover:brightness-125"
                    style={{ borderColor: theme.global.border, color: theme.global.textSecondary }}
                  >
                    立即檢查
                  </button>
                </div>
              </div>

              {/* 展開：風機健康狀態 */}
              {selectedFarm === farm.id && Object.keys(farm.turbines).length > 0 && (
                <div className="mt-3 pt-2 border-t space-y-1" style={{ borderColor: theme.global.border }}>
                  <div className="text-[10px] font-medium mb-1" style={{ color: theme.global.textSecondary }}>
                    風機健康狀態
                  </div>
                  {Object.values(farm.turbines).map((t) => (
                    <div key={t.turbine_id} className="flex items-center justify-between text-[10px] py-0.5">
                      <span className="flex items-center gap-1">
                        {healthIcon(t.health_level)} {t.turbine_id}
                      </span>
                      <span style={{ color: t.health_score < 60 ? '#ef4444' : t.health_score < 80 ? '#eab308' : theme.global.textSecondary }}>
                        {t.health_score >= 0 ? `${t.health_score}/100` : '—'}
                        {t.anomaly_count > 0 && ` · ${t.anomaly_count} 異常`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── 工單列表 ── */}
      {tab === 'tickets' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {tickets.length === 0 && (
            <div className="text-center py-12 text-xs" style={{ color: theme.global.textMuted }}>
              目前無待處理工單
            </div>
          )}
          {tickets.map((t) => (
            <div
              key={t.id}
              className="rounded-lg border p-3"
              style={{ borderColor: theme.global.border }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: priorityColor(t.priority) }}
                  />
                  <div>
                    <div className="text-xs font-medium">{t.title}</div>
                    <div className="text-[10px]" style={{ color: theme.global.textMuted }}>
                      {t.id} · {t.wind_farm_name} · {t.trigger === 'auto_monitor' ? '自動告警' : '手動建立'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] rounded-full px-2 py-0.5" style={{
                    backgroundColor: t.status === 'in_progress' ? '#22c55e20' : '#6366f120',
                    color: t.status === 'in_progress' ? '#22c55e' : '#6366f1',
                  }}>
                    {t.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── 新增風場表單 ── */

function RegisterForm({
  theme,
  onSubmit,
  onCancel,
}: {
  theme: any
  onSubmit: (data: Record<string, string | number | boolean>) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const [turbineCount, setTurbineCount] = useState('10')
  const [ratedPower, setRatedPower] = useState('20')
  const [sourcePath, setSourcePath] = useState('')
  const [pollInterval, setPollInterval] = useState('60')

  const inputStyle = {
    backgroundColor: theme.global.surface,
    borderColor: theme.global.border,
    color: theme.global.textPrimary,
  }

  return (
    <div className="border-b px-4 py-3 space-y-2" style={{ borderColor: theme.global.border, backgroundColor: theme.global.surfaceAlt || theme.global.surface }}>
      <div className="text-xs font-semibold" style={{ color: theme.global.textPrimary }}>新增風場客戶</div>
      <div className="grid grid-cols-2 gap-2">
        <input placeholder="風場名稱 *" value={name} onChange={(e) => setName(e.target.value)} className="rounded border px-2 py-1 text-[11px]" style={inputStyle} />
        <input placeholder="位置" value={location} onChange={(e) => setLocation(e.target.value)} className="rounded border px-2 py-1 text-[11px]" style={inputStyle} />
        <input placeholder="風機數" value={turbineCount} onChange={(e) => setTurbineCount(e.target.value)} className="rounded border px-2 py-1 text-[11px]" style={inputStyle} type="number" />
        <input placeholder="總容量 (MW)" value={ratedPower} onChange={(e) => setRatedPower(e.target.value)} className="rounded border px-2 py-1 text-[11px]" style={inputStyle} type="number" />
        <input placeholder="SCADA 資料路徑" value={sourcePath} onChange={(e) => setSourcePath(e.target.value)} className="col-span-2 rounded border px-2 py-1 text-[11px]" style={inputStyle} />
        <input placeholder="輪詢間隔 (分鐘)" value={pollInterval} onChange={(e) => setPollInterval(e.target.value)} className="rounded border px-2 py-1 text-[11px]" style={inputStyle} type="number" />
      </div>
      <div className="flex gap-2 justify-end">
        <button onClick={onCancel} className="rounded px-3 py-1 text-[10px]" style={{ color: theme.global.textMuted }}>取消</button>
        <button
          onClick={() => name && onSubmit({ name, location, turbine_count: parseInt(turbineCount) || 0, rated_power_mw: parseFloat(ratedPower) || 0, source_path: sourcePath, poll_interval_min: parseInt(pollInterval) || 60 })}
          className="rounded px-3 py-1 text-[10px] font-medium"
          style={{ backgroundColor: theme.global.accent, color: '#fff' }}
        >
          註冊
        </button>
      </div>
    </div>
  )
}
