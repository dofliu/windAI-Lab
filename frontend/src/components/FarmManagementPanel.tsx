/**
 * FarmManagementPanel — 多風場總覽卡片、跨風機比較與風場管理（建立風場 / 群組 / 風機歸屬）。
 */

import { useCallback, useEffect, useState } from 'react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface FarmOverview {
  farm_id: string
  name: string
  customer: string
  capacity_mw: number
  turbine_count: number
  active_alerts: number
  critical_alerts: number
  open_work_orders: number
}

interface TurbineCompare {
  turbine_id: string
  group_name: string | null
  rated_power_kw: number
  active_alerts: number
  critical_alerts: number
  open_work_orders: number
}

interface FarmGroup {
  id: string
  name: string
}

export default function FarmManagementPanel() {
  const { theme } = useTheme()
  const [farms, setFarms] = useState<FarmOverview[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [turbines, setTurbines] = useState<TurbineCompare[]>([])
  const [groups, setGroups] = useState<FarmGroup[]>([])
  const [msg, setMsg] = useState<string | null>(null)
  const [newFarm, setNewFarm] = useState({ name: '', customer: '', capacity_mw: '' })
  const [newGroup, setNewGroup] = useState('')
  const [newTurbine, setNewTurbine] = useState({ turbine_id: '', group_id: '' })

  const fetchOverview = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/farms/overview`)
      if (res.ok) setFarms((await res.json()).farms ?? [])
    } catch (e) {
      console.error('無法載入風場總覽:', e)
    }
  }, [])

  const fetchDetail = useCallback(async (farmId: string) => {
    try {
      const [cmp, hier] = await Promise.all([
        fetch(`${API_BASE}/farms/${farmId}/compare`),
        fetch(`${API_BASE}/farms/${farmId}`),
      ])
      if (cmp.ok) setTurbines((await cmp.json()).turbines ?? [])
      if (hier.ok) setGroups((await hier.json()).farm?.groups ?? [])
    } catch (e) {
      console.error('無法載入風場明細:', e)
    }
  }, [])

  useEffect(() => {
    fetchOverview()
  }, [fetchOverview])

  useEffect(() => {
    if (selectedId) fetchDetail(selectedId)
  }, [selectedId, fetchDetail])

  const refresh = async () => {
    await fetchOverview()
    if (selectedId) await fetchDetail(selectedId)
  }

  const post = async (path: string, body: object, okMsg: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        setMsg(`✅ ${okMsg}`)
        return true
      }
      const err = await res.json().catch(() => ({}))
      setMsg(`❌ ${err.detail ?? `請求失敗 (${res.status})`}`)
    } catch (e) {
      setMsg(`❌ 連線 API 失敗: ${e}`)
    }
    return false
  }

  const handleCreateFarm = async () => {
    if (!newFarm.name.trim()) return
    const ok = await post(
      '/farms',
      {
        name: newFarm.name.trim(),
        customer: newFarm.customer.trim(),
        capacity_mw: Number(newFarm.capacity_mw) || 0,
      },
      `已建立風場 ${newFarm.name.trim()}`,
    )
    if (ok) {
      setNewFarm({ name: '', customer: '', capacity_mw: '' })
      await fetchOverview()
    }
  }

  const handleCreateGroup = async () => {
    if (!selectedId || !newGroup.trim()) return
    if (await post(`/farms/${selectedId}/groups`, { name: newGroup.trim() }, '已建立群組')) {
      setNewGroup('')
      await refresh()
    }
  }

  const handleAssignTurbine = async () => {
    if (!selectedId || !newTurbine.turbine_id.trim()) return
    const ok = await post(
      `/farms/${selectedId}/turbines`,
      { turbine_id: newTurbine.turbine_id.trim(), group_id: newTurbine.group_id || null },
      `已歸屬風機 ${newTurbine.turbine_id.trim()}`,
    )
    if (ok) {
      setNewTurbine({ turbine_id: '', group_id: '' })
      await refresh()
    }
  }

  const handleDeleteFarm = async (farm: FarmOverview) => {
    if (!window.confirm(`確定刪除風場「${farm.name}」？群組與風機歸屬會一併移除。`)) return
    try {
      const res = await fetch(`${API_BASE}/farms/${farm.farm_id}`, { method: 'DELETE' })
      setMsg(res.ok ? `✅ 已刪除風場 ${farm.name}` : `❌ 刪除失敗 (${res.status})`)
      if (res.ok) {
        if (selectedId === farm.farm_id) setSelectedId(null)
        await fetchOverview()
      }
    } catch (e) {
      setMsg(`❌ 連線 API 失敗: ${e}`)
    }
  }

  const inputCls = 'rounded border px-2 py-1 text-[10px] bg-transparent'
  const inputStyle = { borderColor: theme.global.border, color: theme.global.textPrimary }
  const btnCls = 'rounded px-3 py-1 text-[10px] font-semibold text-white hover:brightness-110'
  const selected = farms.find((f) => f.farm_id === selectedId)

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
          🌬️ 風場管理
        </h3>
        <p className="text-[9px]" style={{ color: theme.global.textMuted }}>
          多風場總覽：風機數、使用中告警與開放工單；點選風場查看各風機比較。
        </p>
      </div>

      {msg && (
        <div className="rounded p-2 text-[10px]" style={{ color: theme.global.textPrimary }}>
          {msg}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          className={inputCls}
          style={inputStyle}
          placeholder="風場名稱"
          value={newFarm.name}
          onChange={(e) => setNewFarm({ ...newFarm, name: e.target.value })}
        />
        <input
          className={inputCls}
          style={inputStyle}
          placeholder="客戶"
          value={newFarm.customer}
          onChange={(e) => setNewFarm({ ...newFarm, customer: e.target.value })}
        />
        <input
          className={`${inputCls} w-24`}
          style={inputStyle}
          placeholder="容量 MW"
          type="number"
          min="0"
          value={newFarm.capacity_mw}
          onChange={(e) => setNewFarm({ ...newFarm, capacity_mw: e.target.value })}
        />
        <button className={`${btnCls} bg-emerald-600`} onClick={handleCreateFarm}>
          新增風場
        </button>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {farms.map((farm) => (
          <div
            key={farm.farm_id}
            role="button"
            tabIndex={0}
            onClick={() => setSelectedId(farm.farm_id)}
            onKeyDown={(e) => e.key === 'Enter' && setSelectedId(farm.farm_id)}
            className="cursor-pointer rounded border p-3 transition-all hover:brightness-110"
            style={{
              borderColor: farm.farm_id === selectedId ? '#06b6d4' : theme.global.border,
              color: theme.global.textPrimary,
            }}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs font-semibold">{farm.name}</div>
                <div className="text-[9px]" style={{ color: theme.global.textMuted }}>
                  {farm.customer || '—'} · {farm.capacity_mw} MW
                </div>
              </div>
              <button
                className="text-[9px] text-red-400 hover:text-red-300"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteFarm(farm)
                }}
              >
                刪除
              </button>
            </div>
            <div className="mt-2 grid grid-cols-3 gap-2 text-center text-[10px]">
              <div>
                <div className="text-base font-bold">{farm.turbine_count}</div>
                <div style={{ color: theme.global.textMuted }}>風機</div>
              </div>
              <div>
                <div
                  className={`text-base font-bold ${farm.critical_alerts > 0 ? 'text-red-400' : ''}`}
                >
                  {farm.active_alerts}
                </div>
                <div style={{ color: theme.global.textMuted }}>
                  告警{farm.critical_alerts > 0 ? `（${farm.critical_alerts} 嚴重）` : ''}
                </div>
              </div>
              <div>
                <div className="text-base font-bold">{farm.open_work_orders}</div>
                <div style={{ color: theme.global.textMuted }}>開放工單</div>
              </div>
            </div>
          </div>
        ))}
        {farms.length === 0 && (
          <div className="p-4 text-[10px]" style={{ color: theme.global.textMuted }}>
            尚未建立任何風場。
          </div>
        )}
      </div>

      {selected && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold" style={{ color: theme.global.textPrimary }}>
            {selected.name} — 風機比較
          </h4>
          <div className="flex flex-wrap items-center gap-2">
            <input
              className={inputCls}
              style={inputStyle}
              placeholder="群組名稱"
              value={newGroup}
              onChange={(e) => setNewGroup(e.target.value)}
            />
            <button className={`${btnCls} bg-indigo-600`} onClick={handleCreateGroup}>
              新增群組
            </button>
            <input
              className={inputCls}
              style={inputStyle}
              placeholder="風機 ID"
              value={newTurbine.turbine_id}
              onChange={(e) => setNewTurbine({ ...newTurbine, turbine_id: e.target.value })}
            />
            <select
              className={inputCls}
              style={inputStyle}
              value={newTurbine.group_id}
              onChange={(e) => setNewTurbine({ ...newTurbine, group_id: e.target.value })}
            >
              <option value="">（不指定群組）</option>
              {groups.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </select>
            <button className={`${btnCls} bg-cyan-600`} onClick={handleAssignTurbine}>
              歸屬風機
            </button>
          </div>
          <table className="w-full border-collapse text-left text-[10px]">
            <thead style={{ color: theme.global.textMuted }}>
              <tr>
                <th className="p-2">風機</th>
                <th className="p-2">群組</th>
                <th className="p-2 text-right">額定 kW</th>
                <th className="p-2 text-right">使用中告警</th>
                <th className="p-2 text-right">嚴重</th>
                <th className="p-2 text-right">開放工單</th>
              </tr>
            </thead>
            <tbody style={{ color: theme.global.textPrimary }}>
              {turbines.map((t) => (
                <tr key={t.turbine_id} className="border-t" style={{ borderColor: theme.global.border + '40' }}>
                  <td className="p-2 font-mono">{t.turbine_id}</td>
                  <td className="p-2">{t.group_name ?? '—'}</td>
                  <td className="p-2 text-right">{t.rated_power_kw}</td>
                  <td className="p-2 text-right">{t.active_alerts}</td>
                  <td className={`p-2 text-right ${t.critical_alerts > 0 ? 'text-red-400' : ''}`}>
                    {t.critical_alerts}
                  </td>
                  <td className="p-2 text-right">{t.open_work_orders}</td>
                </tr>
              ))}
              {turbines.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-4 text-center" style={{ color: theme.global.textMuted }}>
                    此風場尚未歸屬任何風機。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
