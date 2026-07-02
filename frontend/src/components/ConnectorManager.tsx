/**
 * ConnectorManager — 資料對接連接器管理器。
 *
 * 支援顯示當前連接器狀態、動態 Toggle 啟閉，
 * 以及新增 Mock/REST/MQTT 連接器。
 */

import { useState, useEffect } from 'react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface ConnectorStatus {
  id: string
  name: string
  type: string
  interval: number
  is_connected: boolean
  last_fetch_time: string | null
  fetch_count: number
}

export default function ConnectorManager() {
  const { theme } = useTheme()
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [showAddModal, setShowAddModal] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  
  // 新增連接器 Form States
  const [newId, setNewId] = useState('')
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('mock')
  const [newInterval, setNewInterval] = useState(60)
  const [newConfigText, setNewConfigText] = useState('{\n  "turbine_id": "WT-01"\n}')

  const fetchConnectors = async () => {
    try {
      const res = await fetch(`${API_BASE}/connectors`)
      if (res.ok) {
        const data = await res.json()
        setConnectors(data)
      }
    } catch (e) {
      console.error('無法載入連接器清單:', e)
    }
  }

  useEffect(() => {
    fetchConnectors()
    // 每 5 秒自動重新整理一次狀態
    const interval = setInterval(fetchConnectors, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleToggle = async (id: string, currentlyEnabled: boolean) => {
    try {
      const res = await fetch(`${API_BASE}/connectors/${id}/toggle?enabled=${!currentlyEnabled}`, {
        method: 'POST',
      })
      if (res.ok) {
        await fetchConnectors()
      } else {
        alert('操作失敗，請確認該連接器設定檔是否存在。')
      }
    } catch (e) {
      console.error('Toggle 連接器出錯:', e)
    }
  }

  // 根據選擇的 Type，預載 config JSON 範本
  const handleTypeChange = (type: string) => {
    setNewType(type)
    if (type === 'mock') {
      setNewConfigText('{\n  "turbine_id": "WT-01"\n}')
    } else if (type === 'rest') {
      setNewConfigText('{\n  "url": "http://api.mockwind.com/scada/latest",\n  "turbine_id": "WT-01"\n}')
    } else if (type === 'mqtt') {
      setNewConfigText('{\n  "host": "localhost",\n  "port": 1883,\n  "topic": "wind/scada",\n  "turbine_id": "WT-01"\n}')
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    let parsedConfig = {}
    try {
      parsedConfig = JSON.parse(newConfigText)
    } catch (err) {
      setErrorMessage('Config JSON 格式不正確')
      return
    }

    const payload = {
      id: newId.trim(),
      name: newName.trim(),
      type: newType,
      interval_seconds: newInterval,
      enabled: true,
      config: parsedConfig,
    }

    try {
      const res = await fetch(`${API_BASE}/connectors`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        setShowAddModal(false)
        setNewId('')
        setNewName('')
        await fetchConnectors()
      } else {
        const errData = await res.json()
        setErrorMessage(errData.detail || '新增連接器失敗')
      }
    } catch (e) {
      setErrorMessage(`連線 API 出錯：${e}`)
    }
  }

  const formatTime = (iso: string | null) => {
    if (!iso) return '尚未拉取'
    const d = new Date(iso)
    return d.toLocaleString('zh-TW', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div className="space-y-4">
      {/* 標題與新增按鈕 */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
            🔌 即時資料對接監控
          </h3>
          <p className="text-[9px]" style={{ color: theme.global.textMuted }}>
            管理風場 SCADA 資料來源連接器，定時拉取將會自動清洗並觸發 WindGuard 異常分析
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="rounded-lg border px-3 py-1.5 text-[10px] font-semibold transition-colors hover:brightness-110"
          style={{ borderColor: theme.global.border, color: theme.global.accent }}
        >
          + 新增連接器
        </button>
      </div>

      {/* 連接器清單 Table */}
      <div className="rounded-lg border overflow-hidden" style={{ borderColor: theme.global.border + '40' }}>
        <table className="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr style={{ backgroundColor: theme.global.panelBg + '80', color: theme.global.textSecondary }}>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>連接器名稱</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>類型</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>時間間隔 (秒)</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>連線狀態</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>最後拉取時間</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>累計拉取</th>
              <th className="p-2 border-b text-center" style={{ borderColor: theme.global.border + '40' }}>啟用開關</th>
            </tr>
          </thead>
          <tbody>
            {connectors.map(conn => (
              <tr key={conn.id} style={{ color: theme.global.textPrimary }}>
                <td className="p-2 border-b font-medium" style={{ borderColor: theme.global.border + '40' }}>
                  <div>{conn.name}</div>
                  <div className="text-[8px] opacity-60 font-mono">{conn.id}</div>
                </td>
                <td className="p-2 border-b font-mono uppercase" style={{ borderColor: theme.global.border + '40' }}>
                  {conn.type}
                </td>
                <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                  {conn.interval} 秒
                </td>
                <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: conn.is_connected ? '#22c55e' : '#ef4444' }} />
                    <span style={{ color: conn.is_connected ? '#22c55e' : '#ef4444' }}>
                      {conn.is_connected ? 'Connected' : 'Offline'}
                    </span>
                  </span>
                </td>
                <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                  {formatTime(conn.last_fetch_time)}
                </td>
                <td className="p-2 border-b font-mono" style={{ borderColor: theme.global.border + '40' }}>
                  {conn.fetch_count} 次
                </td>
                <td className="p-2 border-b text-center" style={{ borderColor: theme.global.border + '40' }}>
                  <button
                    onClick={() => handleToggle(conn.id, conn.is_connected)}
                    className="rounded px-2.5 py-1 text-[9px] font-semibold text-white transition-colors"
                    style={{ backgroundColor: conn.is_connected ? '#ef4444' : '#22c55e' }}
                  >
                    {conn.is_connected ? '停用' : '啟用'}
                  </button>
                </td>
              </tr>
            ))}
            {connectors.length === 0 && (
              <tr>
                <td colSpan={7} className="p-4 text-center text-muted" style={{ color: theme.global.textMuted }}>
                  目前無設定任何資料連接器
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 新增連接器 Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div
            className="w-full max-w-md rounded-lg border p-4 space-y-4 shadow-xl"
            style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
          >
            <h4 className="text-xs font-bold" style={{ color: theme.global.textPrimary }}>
              🔌 新增 SCADA 資料連接器
            </h4>

            <form onSubmit={handleCreate} className="space-y-3 text-[10px]">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span style={{ color: theme.global.textSecondary }}>連接器 ID (不可重)：</span>
                  <input
                    required
                    value={newId}
                    onChange={e => setNewId(e.target.value)}
                    placeholder="例如：kelmarsh_wt2"
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                  />
                </div>
                <div className="space-y-1">
                  <span style={{ color: theme.global.textSecondary }}>連接器名稱：</span>
                  <input
                    required
                    value={newName}
                    onChange={e => setNewName(e.target.value)}
                    placeholder="例如：風機 WT-02 資料源"
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <span style={{ color: theme.global.textSecondary }}>連接器類型：</span>
                  <select
                    value={newType}
                    onChange={e => handleTypeChange(e.target.value)}
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                  >
                    <option value="mock">MOCK (本地模擬)</option>
                    <option value="rest">REST (外部 HTTP GET)</option>
                    <option value="mqtt">MQTT (訂閱 Broker)</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <span style={{ color: theme.global.textSecondary }}>拉取間隔 (秒)：</span>
                  <input
                    type="number"
                    required
                    min={5}
                    value={newInterval}
                    onChange={e => setNewInterval(parseInt(e.target.value))}
                    className="w-full rounded border px-2 py-1 text-xs outline-none"
                    style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <span style={{ color: theme.global.textSecondary }}>
                  Config 核心參數 (JSON 格式)：
                </span>
                <textarea
                  rows={5}
                  required
                  value={newConfigText}
                  onChange={e => setNewConfigText(e.target.value)}
                  className="w-full rounded border px-2 py-1 text-xs font-mono outline-none resize-none"
                  style={{ borderColor: theme.global.border, backgroundColor: theme.global.pageBg, color: theme.global.textPrimary }}
                />
              </div>

              {errorMessage && (
                <div className="text-[9px] text-red-500 font-medium">
                  ⚠️ {errorMessage}
                </div>
              )}

              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="rounded border px-3 py-1.5 text-[9px] font-semibold transition-colors"
                  style={{ borderColor: theme.global.border, color: theme.global.textMuted }}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="rounded px-4 py-1.5 text-[9px] font-semibold text-white transition-colors"
                  style={{ backgroundColor: theme.global.accent }}
                >
                  確認建立與啟用
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
