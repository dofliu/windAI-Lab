import { useState, useEffect, useCallback } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  BarChart,
  Bar,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts'

/* ── Types ── */

interface ScatterPoint { windSpeed: number; power: number }
interface TrendPoint { date: string; windSpeed: number; power: number }
interface StatEntry { mean: number | null; std: number | null; min: number | null; max: number | null }
interface ScadaData {
  turbine_id: string
  total_records: number
  scatter: ScatterPoint[]
  trend: TrendPoint[]
  statistics: Record<string, StatEntry>
}

interface FeatureImportance {
  column: string
  correlation: number | null
  abs_correlation: number | null
  spearman: number | null
  mutual_info: number | null
  composite_score: number | null
}

interface CorrelationPair {
  col_a: string
  col_b: string
  pearson: number | null
  abs_pearson: number | null
}

interface AnomalyColumn {
  column: string
  iqr_outliers: number
  iqr_outlier_pct: number | null
  zscore_outliers: number
}

interface Distribution {
  column: string
  distribution_type: string
  skewness: number | null
  kurtosis: number | null
  histogram: Array<{ bin_start: number | null; bin_end: number | null; count: number }>
  zero_pct: number | null
}

interface Recommendation {
  type: 'success' | 'warning' | 'info'
  title: string
  detail: string
}

interface FeatureData {
  target_column: string | null
  total_rows: number
  numeric_columns: number
  feature_importance: FeatureImportance[]
  correlations: { top_pairs: CorrelationPair[] }
  anomalies: { columns: AnomalyColumn[]; total_columns_with_outliers: number }
  distributions: Distribution[]
  recommendations: Recommendation[]
}

/* ── Helpers ── */

function safeJsonParse(text: string): unknown {
  // Replace NaN, Infinity, -Infinity with null before parsing
  const cleaned = text.replace(/:\s*(NaN|-?Infinity)\b/g, ': null')
  return JSON.parse(cleaned)
}

const CHART_COLORS = ['#06b6d4', '#a78bfa', '#34d399', '#fbbf24', '#f87171', '#818cf8', '#fb923c', '#2dd4bf', '#e879f9', '#38bdf8']
const REC_ICONS: Record<string, string> = { success: '✅', warning: '⚠️', info: 'ℹ️' }
const REC_STYLES: Record<string, string> = {
  success: 'bg-emerald-900/30 border-emerald-800/50 text-emerald-300',
  warning: 'bg-amber-900/30 border-amber-800/50 text-amber-300',
  info: 'bg-blue-900/30 border-blue-800/50 text-blue-300',
}

/* ── Component ── */

export default function ScadaDashboard() {
  const [data, setData] = useState<ScadaData | null>(null)
  const [featureData, setFeatureData] = useState<FeatureData | null>(null)
  const [loading, setLoading] = useState(false)
  const [featureLoading, setFeatureLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [turbineId, setTurbineId] = useState('Kelmarsh_1')
  const [activeTab, setActiveTab] = useState<'scatter' | 'trend' | 'stats' | 'features'>('scatter')
  const [turbines, setTurbines] = useState<string[]>(['Kelmarsh_1', 'Kelmarsh_2', 'Kelmarsh_3', 'Kelmarsh_4', 'Kelmarsh_5', 'Kelmarsh_6'])

  // 從後端動態取得風機列表
  useEffect(() => {
    fetch('http://localhost:8000/api/scada/turbines')
      .then((res) => res.json())
      .then((data) => {
        if (data.turbines && data.turbines.length > 0) {
          setTurbines(data.turbines)
          if (!data.turbines.includes(turbineId)) {
            setTurbineId(data.turbines[0])
          }
        }
      })
      .catch(() => { /* 後端未啟動時保留 fallback */ })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`http://localhost:8000/api/scada/${turbineId}/overview?limit=2000`)
      const text = await res.text()
      const json = safeJsonParse(text) as Record<string, unknown>
      if (json.status === 'error') {
        setError((json.detail as string) || '載入失敗')
      } else {
        setData(json as unknown as ScadaData)
      }
    } catch {
      setError('無法連線至後端')
    } finally {
      setLoading(false)
    }
  }, [turbineId])

  const loadFeatures = useCallback(async () => {
    setFeatureLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/api/scada/${turbineId}/features`)
      const text = await res.text()
      const json = safeJsonParse(text) as Record<string, unknown>
      if (json.status === 'success') {
        setFeatureData(json as unknown as FeatureData)
      }
    } catch {
      // Feature analysis not available
    } finally {
      setFeatureLoading(false)
    }
  }, [turbineId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Load features when tab is selected
  useEffect(() => {
    if (activeTab === 'features' && !featureData) {
      loadFeatures()
    }
  }, [activeTab, featureData, loadFeatures])

  // Reset feature data when turbine changes
  useEffect(() => {
    setFeatureData(null)
  }, [turbineId])

  const statsBarData = data?.statistics
    ? Object.entries(data.statistics)
        .filter(([k]) => !k.includes('timestamp') && !k.includes('time'))
        .slice(0, 10)
        .map(([key, val]) => ({
          name: key.length > 22 ? key.slice(0, 20) + '…' : key,
          mean: val.mean ?? 0,
          std: val.std ?? 0,
        }))
    : []

  const tabs = [
    { key: 'scatter' as const, label: '⚡ 功率曲線' },
    { key: 'trend' as const, label: '📈 趨勢圖' },
    { key: 'stats' as const, label: '📋 統計量' },
    { key: 'features' as const, label: '🔬 特徵分析' },
  ]

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-200">📊 SCADA 資料儀表板</h3>
        <div className="flex items-center gap-3">
          <select
            value={turbineId}
            onChange={(e) => setTurbineId(e.target.value)}
            className="rounded-md bg-slate-700 px-3 py-1.5 text-xs text-slate-200 outline-none ring-1 ring-slate-600 focus:ring-cyan-500"
          >
            {turbines.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <button
            onClick={loadData}
            disabled={loading}
            className="rounded-md bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-cyan-500 disabled:opacity-50"
          >
            {loading ? '載入中...' : '重新整理'}
          </button>
        </div>
      </div>

      {error && <div className="rounded-md bg-red-900/30 px-3 py-2 text-xs text-red-400">{error}</div>}

      {data && (
        <>
          {/* Info bar */}
          <div className="flex items-center gap-4 rounded-md bg-slate-800/60 px-4 py-2 text-xs">
            <span className="text-slate-500">風機：<span className="font-medium text-slate-300">{data.turbine_id}</span></span>
            <span className="text-slate-500">記錄數：<span className="font-medium text-slate-300">{data.total_records.toLocaleString()}</span></span>
          </div>

          {/* Tabs */}
          <div className="flex gap-1">
            {tabs.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  activeTab === key
                    ? 'bg-slate-700 text-slate-200 ring-1 ring-slate-600'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* ════ Scatter ════ */}
          {activeTab === 'scatter' && data.scatter.length > 0 && (
            <div className="flex-1 min-h-[300px]">
              <p className="mb-2 text-[10px] text-slate-500">風速 vs 發電功率散佈圖（{data.scatter.length} 點）</p>
              <ResponsiveContainer width="100%" height="90%">
                <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="windSpeed" name="風速" unit=" m/s" type="number"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    label={{ value: '風速 (m/s)', position: 'bottom', fontSize: 11, fill: '#64748b', offset: -5 }} />
                  <YAxis dataKey="power" name="功率" unit=" kW" type="number"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    label={{ value: '功率 (kW)', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#64748b' }} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 11 }} />
                  <Scatter data={data.scatter} fill="#06b6d4" fillOpacity={0.35} r={2.5} />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
          {activeTab === 'scatter' && data.scatter.length === 0 && (
            <div className="flex flex-1 items-center justify-center">
              <p className="text-sm text-slate-600">無散佈圖資料 — 請確認後端已連線</p>
            </div>
          )}

          {/* ════ Trend ════ */}
          {activeTab === 'trend' && data.trend.length > 0 && (
            <div className="flex-1 min-h-[300px]">
              <p className="mb-2 text-[10px] text-slate-500">近 {data.trend.length} 天每日平均趨勢</p>
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={data.trend} margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: '#94a3b8' }} interval="preserveStartEnd" />
                  <YAxis yAxisId="ws" orientation="left" tick={{ fontSize: 10, fill: '#06b6d4' }}
                    label={{ value: '風速 (m/s)', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#06b6d4' }} />
                  <YAxis yAxisId="pw" orientation="right" tick={{ fontSize: 10, fill: '#a78bfa' }}
                    label={{ value: '功率 (kW)', angle: 90, position: 'insideRight', fontSize: 11, fill: '#a78bfa' }} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 11 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line yAxisId="ws" type="monotone" dataKey="windSpeed" stroke="#06b6d4" name="風速 (m/s)" dot={false} strokeWidth={2} />
                  <Line yAxisId="pw" type="monotone" dataKey="power" stroke="#a78bfa" name="功率 (kW)" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          {activeTab === 'trend' && data.trend.length === 0 && (
            <div className="flex flex-1 items-center justify-center"><p className="text-sm text-slate-600">無趨勢資料</p></div>
          )}

          {/* ════ Stats ════ */}
          {activeTab === 'stats' && statsBarData.length > 0 && (
            <div className="flex-1 min-h-[300px]">
              <p className="mb-2 text-[10px] text-slate-500">各欄位平均值</p>
              <ResponsiveContainer width="100%" height="90%">
                <BarChart data={statsBarData} margin={{ top: 10, right: 20, bottom: 60, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8', angle: -35, textAnchor: 'end' }} height={70} />
                  <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 11 }} />
                  <Bar dataKey="mean" name="平均值" radius={[4, 4, 0, 0]}>
                    {statsBarData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} fillOpacity={0.8} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* ════ Feature Analysis ════ */}
          {activeTab === 'features' && (
            <div className="flex-1 overflow-y-auto space-y-4">
              {featureLoading && (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-r-transparent" />
                    <p className="mt-3 text-xs text-slate-400">分析中... 正在計算 {data.total_records.toLocaleString()} 筆資料的特徵</p>
                  </div>
                </div>
              )}

              {featureData && !featureLoading && (
                <>
                  {/* Overview stats */}
                  <div className="grid grid-cols-3 gap-2">
                    <div className="rounded-lg bg-slate-800/80 p-3 text-center">
                      <div className="text-lg font-bold text-cyan-400">{featureData.numeric_columns}</div>
                      <div className="text-[10px] text-slate-500">分析欄位數</div>
                    </div>
                    <div className="rounded-lg bg-slate-800/80 p-3 text-center">
                      <div className="text-lg font-bold text-purple-400">{featureData.feature_importance.length}</div>
                      <div className="text-[10px] text-slate-500">特徵排序</div>
                    </div>
                    <div className="rounded-lg bg-slate-800/80 p-3 text-center">
                      <div className="text-lg font-bold text-amber-400">{featureData.anomalies.total_columns_with_outliers}</div>
                      <div className="text-[10px] text-slate-500">含異常值欄位</div>
                    </div>
                  </div>

                  {/* Recommendations */}
                  {featureData.recommendations.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-slate-400">💡 智慧建議</h4>
                      {featureData.recommendations.map((rec, i) => (
                        <div key={i} className={`rounded-lg border px-3 py-2 text-xs ${REC_STYLES[rec.type] || ''}`}>
                          <span className="mr-1">{REC_ICONS[rec.type]}</span>
                          <span className="font-semibold">{rec.title}</span>
                          <p className="mt-1 opacity-80">{rec.detail}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Feature Importance — Top 10 bar chart */}
                  {featureData.feature_importance.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold text-slate-400">
                        🎯 特徵重要度 Top 10
                        <span className="ml-2 font-normal text-slate-600">
                          （目標：{featureData.target_column}）
                        </span>
                      </h4>
                      <div className="h-[280px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={featureData.feature_importance.slice(0, 10).map((f) => ({
                              name: f.column.length > 25 ? f.column.slice(0, 23) + '…' : f.column,
                              score: f.composite_score ?? 0,
                              corr: Math.abs(f.correlation ?? 0),
                              spearman: Math.abs(f.spearman ?? 0),
                            }))}
                            layout="vertical"
                            margin={{ top: 5, right: 30, bottom: 5, left: 150 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis type="number" domain={[0, 1]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                            <YAxis type="category" dataKey="name" tick={{ fontSize: 9, fill: '#94a3b8' }} width={145} />
                            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 11 }} />
                            <Bar dataKey="score" name="綜合分數" fill="#8b5cf6" fillOpacity={0.8} radius={[0, 4, 4, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}

                  {/* Top Correlations */}
                  {featureData.correlations.top_pairs.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold text-slate-400">🔗 高相關欄位對 Top 10</h4>
                      <div className="space-y-1">
                        {featureData.correlations.top_pairs.slice(0, 10).map((pair, i) => (
                          <div key={i} className="flex items-center gap-2 rounded bg-slate-800/60 px-3 py-1.5 text-[11px]">
                            <span className="w-5 text-slate-600">{i + 1}.</span>
                            <span className="flex-1 truncate text-slate-300" title={pair.col_a}>
                              {pair.col_a.length > 20 ? pair.col_a.slice(0, 18) + '…' : pair.col_a}
                            </span>
                            <span className="text-slate-600">↔</span>
                            <span className="flex-1 truncate text-slate-300" title={pair.col_b}>
                              {pair.col_b.length > 20 ? pair.col_b.slice(0, 18) + '…' : pair.col_b}
                            </span>
                            <span className={`font-mono font-bold ${
                              (pair.abs_pearson ?? 0) > 0.9 ? 'text-red-400' :
                              (pair.abs_pearson ?? 0) > 0.7 ? 'text-amber-400' : 'text-slate-400'
                            }`}>
                              {pair.pearson?.toFixed(3)}
                            </span>
                            {/* Visual bar */}
                            <div className="h-1.5 w-16 rounded-full bg-slate-700 overflow-hidden">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-purple-500"
                                style={{ width: `${(pair.abs_pearson ?? 0) * 100}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Anomaly Summary */}
                  {featureData.anomalies.columns.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold text-slate-400">
                        ⚠️ 異常值概況（{featureData.anomalies.total_columns_with_outliers} 個欄位含異常值）
                      </h4>
                      <div className="h-[200px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart
                            data={featureData.anomalies.columns.slice(0, 10).map((a) => ({
                              name: a.column.length > 20 ? a.column.slice(0, 18) + '…' : a.column,
                              pct: a.iqr_outlier_pct ?? 0,
                            }))}
                            margin={{ top: 5, right: 20, bottom: 50, left: 10 }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="name" tick={{ fontSize: 8, fill: '#94a3b8', angle: -40, textAnchor: 'end' }} height={60} />
                            <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} label={{ value: '異常比例 (%)', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#64748b' }} />
                            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, fontSize: 11 }} />
                            <Bar dataKey="pct" name="IQR 異常%" fill="#f87171" fillOpacity={0.7} radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  )}

                  {/* Distribution types summary */}
                  {featureData.distributions.length > 0 && (() => {
                    const distCounts: Record<string, number> = {}
                    featureData.distributions.forEach((d) => {
                      distCounts[d.distribution_type] = (distCounts[d.distribution_type] || 0) + 1
                    })
                    const radarData = Object.entries(distCounts).map(([type, count]) => ({
                      type,
                      count,
                    }))
                    return (
                      <div>
                        <h4 className="mb-2 text-xs font-semibold text-slate-400">📊 欄位分佈類型</h4>
                        <div className="h-[220px]">
                          <ResponsiveContainer width="100%" height="100%">
                            <RadarChart data={radarData}>
                              <PolarGrid stroke="#334155" />
                              <PolarAngleAxis dataKey="type" tick={{ fontSize: 10, fill: '#94a3b8' }} />
                              <PolarRadiusAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                              <Radar dataKey="count" name="欄位數" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.3} />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )
                  })()}
                </>
              )}

              {!featureData && !featureLoading && (
                <div className="flex flex-col items-center justify-center py-12 gap-3">
                  <p className="text-sm text-slate-600">點擊下方按鈕開始特徵分析</p>
                  <button
                    onClick={loadFeatures}
                    className="rounded-lg bg-purple-600 px-4 py-2 text-xs font-medium text-white hover:bg-purple-500"
                  >
                    🔬 開始分析
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {!data && !loading && !error && (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-slate-600">連線後端後載入 SCADA 資料...</p>
        </div>
      )}
    </div>
  )
}
