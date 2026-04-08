import { useState, useCallback } from 'react'

interface MLResult {
  status: string
  turbine_id?: string
  models?: {
    nbm?: { status: string; r2?: number; mae?: number; rmse?: number }
    classifier?: { status: string; f1_macro?: number }
    rul?: { status: string; model_type?: string; trend?: string; r_squared?: number }
  }
  nbm_anomalies?: { anomaly_count?: number; anomaly_ratio?: number }
  fault_classification?: {
    fault_counts?: Record<string, number>
    severity_distribution?: { normal?: number; single_fault?: number; multi_fault?: number }
  }
  rul_prediction?: {
    rul_days?: number
    confidence_interval?: { lower?: number; upper?: number }
    trend?: string
    current_health_index?: number
  }
}

export default function MLDashboard() {
  const [trainResult, setTrainResult] = useState<MLResult | null>(null)
  const [inferResult, setInferResult] = useState<MLResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [turbineId, setTurbineId] = useState('Kelmarsh_1')

  const turbines = ['Kelmarsh_1', 'Kelmarsh_2', 'Kelmarsh_3', 'Kelmarsh_4', 'Kelmarsh_5', 'Kelmarsh_6']

  const apiCall = useCallback(async (url: string, setter: (r: MLResult) => void) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(url, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'error') {
        setError(data.detail || '操作失敗')
      } else {
        setter(data)
      }
    } catch {
      setError('無法連線至後端')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleTrain = () => apiCall(`/api/ml/train?turbine_id=${turbineId}`, setTrainResult)
  const handleInfer = () => apiCall(`/api/ml/inference?turbine_id=${turbineId}`, setInferResult)

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-200">🧠 ML Pipeline</h3>
        <div className="flex items-center gap-3">
          <select
            value={turbineId}
            onChange={(e) => setTurbineId(e.target.value)}
            className="rounded-md bg-slate-700 px-3 py-1.5 text-xs text-slate-200 outline-none ring-1 ring-slate-600 focus:ring-indigo-500"
          >
            {turbines.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={handleTrain}
            disabled={loading}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? '...' : '訓練'}
          </button>
          <button
            onClick={handleInfer}
            disabled={loading}
            className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-500 disabled:opacity-50"
          >
            推論
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded bg-red-900/30 px-2 py-1 text-[10px] text-red-400">{error}</div>
      )}

      {/* Training results */}
      {trainResult?.models && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-semibold text-indigo-400">訓練結果</h4>
          <ModelCard
            title="NBM 功率曲線"
            status={trainResult.models.nbm?.status}
            metrics={trainResult.models.nbm?.r2 != null ? [
              { label: 'R²', value: trainResult.models.nbm.r2.toFixed(4) },
              { label: 'MAE', value: `${trainResult.models.nbm.mae?.toFixed(1)} kW` },
            ] : undefined}
          />
          <ModelCard
            title="故障分類器"
            status={trainResult.models.classifier?.status}
            metrics={trainResult.models.classifier?.f1_macro != null ? [
              { label: 'F1 Macro', value: trainResult.models.classifier.f1_macro.toFixed(4) },
            ] : undefined}
          />
          <ModelCard
            title="RUL 退化模型"
            status={trainResult.models.rul?.status}
            metrics={trainResult.models.rul?.r_squared != null ? [
              { label: '模型', value: trainResult.models.rul.model_type ?? '-' },
              { label: 'R²', value: trainResult.models.rul.r_squared.toFixed(4) },
              { label: '趨勢', value: trendLabel(trainResult.models.rul.trend) },
            ] : undefined}
          />
        </div>
      )}

      {/* Inference results */}
      {inferResult && inferResult.status === 'success' && (
        <div className="space-y-2">
          <h4 className="text-[10px] font-semibold text-emerald-400">
            推論結果 — {inferResult.turbine_id}
          </h4>

          {/* Health + RUL */}
          {inferResult.rul_prediction && (
            <div className="rounded bg-slate-800/80 p-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400">健康指標</span>
                <span className={`text-sm font-bold ${healthColor(inferResult.rul_prediction.current_health_index ?? 0)}`}>
                  {inferResult.rul_prediction.current_health_index?.toFixed(1)}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-slate-400">RUL</span>
                <span className="text-xs font-medium text-slate-200">
                  {inferResult.rul_prediction.rul_days?.toFixed(0)} 天
                  <span className="ml-1 text-[9px] text-slate-500">
                    ({inferResult.rul_prediction.confidence_interval?.lower?.toFixed(0)}~
                    {inferResult.rul_prediction.confidence_interval?.upper?.toFixed(0)})
                  </span>
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span className="text-[10px] text-slate-400">趨勢</span>
                <span className="text-[10px]">{trendLabel(inferResult.rul_prediction.trend)}</span>
              </div>
            </div>
          )}

          {/* NBM anomalies */}
          {inferResult.nbm_anomalies && (
            <div className="rounded bg-slate-800/80 p-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400">NBM 異常點</span>
                <span className="text-xs font-medium text-amber-400">
                  {inferResult.nbm_anomalies.anomaly_count}
                  <span className="ml-1 text-[9px] text-slate-500">
                    ({((inferResult.nbm_anomalies.anomaly_ratio ?? 0) * 100).toFixed(1)}%)
                  </span>
                </span>
              </div>
            </div>
          )}

          {/* Fault classification */}
          {inferResult.fault_classification?.severity_distribution && (
            <div className="rounded bg-slate-800/80 p-2">
              <div className="text-[10px] text-slate-400">故障分佈</div>
              <div className="mt-1 flex gap-2 text-[10px]">
                <span className="text-emerald-400">
                  正常 {inferResult.fault_classification.severity_distribution.normal}
                </span>
                <span className="text-amber-400">
                  單一 {inferResult.fault_classification.severity_distribution.single_fault}
                </span>
                <span className="text-red-400">
                  多重 {inferResult.fault_classification.severity_distribution.multi_fault}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!trainResult && !inferResult && !loading && (
        <p className="text-[10px] text-slate-600">選擇風機後按「訓練」開始</p>
      )}
    </div>
  )
}

/* ── Helper components ── */

function ModelCard({ title, status, metrics }: {
  title: string
  status?: string
  metrics?: { label: string; value: string }[]
}) {
  const statusColor = status === 'success' ? 'text-emerald-400' : status === 'error' ? 'text-red-400' : 'text-slate-500'
  return (
    <div className="rounded bg-slate-800/80 p-2">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium text-slate-300">{title}</span>
        <span className={`text-[9px] ${statusColor}`}>{status === 'success' ? '✓' : status ?? '-'}</span>
      </div>
      {metrics && (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
          {metrics.map((m) => (
            <span key={m.label} className="text-[9px] text-slate-400">
              {m.label}: <span className="text-slate-200">{m.value}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function trendLabel(trend?: string): string {
  if (trend === 'degrading') return '退化中 📉'
  if (trend === 'improving') return '改善中 📈'
  return '穩定 ➡️'
}

function healthColor(hi: number): string {
  if (hi >= 80) return 'text-emerald-400'
  if (hi >= 60) return 'text-amber-400'
  return 'text-red-400'
}
