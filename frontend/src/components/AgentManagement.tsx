import { useState, useEffect, useCallback } from 'react'
import { Agent } from '../types/agent'

interface AvailableAgent {
  id: string
  name: string
  display_name: string
  tier: string
  color: string
  icon: string
  description: string
  skills: string[]
}

interface SkillInfo {
  skill_id: string
  display_name: string
  description: string
  version: string
}

/** 內建的可聘用代理清單（後端離線時的 fallback） */
const BUILTIN_AVAILABLE: AvailableAgent[] = [
  { id: 'etl-engineer', name: 'wData:etl-engineer', display_name: 'ETL 工程師', tier: 'data', color: '#10b981', icon: '🔄', description: 'ETL 資料管線建置與自動化', skills: [] },
  { id: 'experiment-tracker', name: 'wAI:experiment-tracker', display_name: '實驗追蹤師', tier: 'ai-ml', color: '#8b5cf6', icon: '📝', description: '記錄實驗參數至 MLflow', skills: [] },
  { id: 'hyperparameter-tuner', name: 'wAI:hyperparameter-tuner', display_name: '超參數調整師', tier: 'ai-ml', color: '#8b5cf6', icon: '🎯', description: 'Optuna 超參數搜索與最佳化', skills: [] },
  { id: 'wake-analyst', name: 'wDomain:wake-analyst', display_name: '尾流分析師', tier: 'domain', color: '#ec4899', icon: '🌀', description: '風場尾流效應模擬與分析', skills: [] },
  { id: 'literature-reviewer', name: 'wRes:literature-reviewer', display_name: '文獻審閱員', tier: 'research', color: '#06b6d4', icon: '📚', description: '系統性文獻搜尋與比較分析', skills: [] },
  { id: 'research-lead', name: 'wLab:research-lead', display_name: '研究主管', tier: 'leadership', color: '#f59e0b', icon: '🎓', description: '審閱實驗設計與論文品質', skills: [] },
  { id: 'tech-lead', name: 'wLab:tech-lead', display_name: '技術主管', tier: 'leadership', color: '#f59e0b', icon: '💻', description: '技術決策與架構審查', skills: [] },
  { id: 'backend-dev', name: 'wEng:backend-dev', display_name: '後端開發師', tier: 'engineering', color: '#f97316', icon: '🖥️', description: 'FastAPI 後端開發', skills: [] },
  { id: 'frontend-dev', name: 'wEng:frontend-dev', display_name: '前端開發師', tier: 'engineering', color: '#f97316', icon: '🎨', description: 'React 前端開發', skills: [] },
  { id: 'report-generator', name: 'wRes:report-generator', display_name: '報告產生器', tier: 'research', color: '#06b6d4', icon: '📄', description: '自動產出分析報告', skills: [] },
]

const BUILTIN_SKILLS: SkillInfo[] = [
  { skill_id: 'scada_ingestion', display_name: 'SCADA 資料載入', description: '自動偵測格式與欄位', version: '1.0.0' },
  { skill_id: 'scada_cleaning', display_name: 'SCADA 資料清洗', description: '去重、插值、異常過濾', version: '1.0.0' },
  { skill_id: 'fault_classification', display_name: '故障分類', description: 'ML 多標籤故障分類', version: '1.0.0' },
  { skill_id: 'nbm_training', display_name: 'NBM 功率曲線訓練', description: 'k-NN 正常行為模型', version: '1.0.0' },
  { skill_id: 'rul_prediction', display_name: 'RUL 壽命預測', description: '退化曲線擬合', version: '1.0.0' },
  { skill_id: 'domain_feature_extraction', display_name: '領域特徵萃取', description: '風力發電專用特徵', version: '1.0.0' },
]

interface Props {
  allAgents?: Agent[]
  onHire?: (agent: AvailableAgent) => void
  onFire?: (agentId: string) => void
}

export default function AgentManagement({ allAgents = [], onHire, onFire }: Props) {
  const [available, setAvailable] = useState<AvailableAgent[]>(BUILTIN_AVAILABLE)
  const [skills, setSkills] = useState<SkillInfo[]>(BUILTIN_SKILLS)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [backendOnline, setBackendOnline] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const [avRes, skRes] = await Promise.all([
        fetch('/api/agents/available'),
        fetch('/api/skills'),
      ])
      const avData = await avRes.json()
      const skData = await skRes.json()
      if (avData.agents?.length > 0) {
        setAvailable(avData.agents)
        setBackendOnline(true)
      }
      if (skData.skills?.length > 0) {
        setSkills(skData.skills)
      }
    } catch {
      // 後端離線，使用內建清單
      setBackendOnline(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  // 過濾掉已在職的代理
  const activeIds = new Set(allAgents.map(a => a.id))
  const filteredAvailable = available.filter(a => !activeIds.has(a.id))

  // 可解聘的代理（非核心的在職代理）
  const CORE_IDS = new Set([
    'project-director', 'project-manager', 'scada-processor', 'quality-checker',
    'fault-diagnostician', 'predictive-modeler', 'anomaly-detector', 'feature-engineer',
    'rag-architect', 'power-curve-expert', 'maintenance-planner', 'paper-writer',
  ])
  const fireableAgents = allAgents.filter(a => !CORE_IDS.has(a.id))

  const hire = async (agent: AvailableAgent) => {
    setLoading(true)
    setMessage(null)

    if (backendOnline) {
      try {
        const res = await fetch(`/api/agents/hire?agent_id=${agent.id}`, { method: 'POST' })
        const data = await res.json()
        if (res.ok) {
          setMessage(`✅ 已聘用 ${data.agent?.display_name ?? agent.display_name}`)
          await fetchData()
        } else {
          setMessage(`❌ ${data.detail}`)
        }
      } catch {
        setMessage('❌ 後端連線失敗')
      }
    } else {
      // 模擬模式：直接透過 callback 新增
      onHire?.(agent)
      setMessage(`✅ 已聘用 ${agent.display_name}（模擬模式）`)
      setAvailable(prev => prev.filter(a => a.id !== agent.id))
    }
    setLoading(false)
  }

  const fire = async (agentId: string) => {
    setLoading(true)
    setMessage(null)
    const agent = allAgents.find(a => a.id === agentId)

    if (backendOnline) {
      try {
        const res = await fetch(`/api/agents/fire?agent_id=${agentId}`, { method: 'POST' })
        const data = await res.json()
        if (res.ok) {
          setMessage(`👋 已解聘 ${agent?.displayName ?? agentId}`)
          await fetchData()
        } else {
          setMessage(`❌ ${data.detail}`)
        }
      } catch {
        setMessage('❌ 後端連線失敗')
      }
    } else {
      // 模擬模式
      onFire?.(agentId)
      setMessage(`👋 已解聘 ${agent?.displayName ?? agentId}（模擬模式）`)
      // 把解聘的代理加回可聘用清單
      if (agent) {
        setAvailable(prev => [...prev, {
          id: agent.id, name: agent.name, display_name: agent.displayName,
          tier: agent.tier, color: agent.color, icon: agent.icon,
          description: '', skills: [],
        }])
      }
    }
    setLoading(false)
  }

  const tierColors: Record<string, string> = {
    leadership: 'text-amber-400 bg-amber-950/40',
    data: 'text-emerald-400 bg-emerald-950/40',
    'ai-ml': 'text-violet-400 bg-violet-950/40',
    domain: 'text-rose-400 bg-rose-950/40',
    engineering: 'text-orange-400 bg-orange-950/40',
    research: 'text-cyan-400 bg-cyan-950/40',
  }

  const tierLabels: Record<string, string> = {
    leadership: '指揮', data: '資料', 'ai-ml': '模型',
    domain: '領域', engineering: '工程', research: '研究',
  }

  return (
    <div className="space-y-4 p-2 overflow-y-auto max-h-full">
      {/* Connection status */}
      <div className="flex items-center gap-2 text-[10px] text-slate-500">
        <div className={`h-1.5 w-1.5 rounded-full ${backendOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
        {backendOnline ? '後端已連線' : '模擬模式（內建資料）'}
      </div>

      {/* Message */}
      {message && (
        <div className="rounded-lg bg-slate-800/60 px-3 py-2 text-xs text-slate-300">
          {message}
        </div>
      )}

      {/* Fireable agents (hired non-core) */}
      {fireableAgents.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
            🏢 已聘用人員（可解聘）({fireableAgents.length})
          </h3>
          <div className="space-y-1">
            {fireableAgents.map((agent) => (
              <div key={agent.id} className="flex items-center gap-2 rounded-lg border border-slate-700/40 bg-slate-800/40 px-3 py-1.5">
                <span className="text-sm">{agent.icon}</span>
                <span className="text-xs text-slate-200 flex-1">{agent.displayName}</span>
                <span className={`rounded px-1 py-0.5 text-[9px] ${tierColors[agent.tier] ?? ''}`}>
                  {tierLabels[agent.tier] ?? agent.tier}
                </span>
                <button
                  onClick={() => fire(agent.id)}
                  disabled={loading}
                  className="rounded bg-red-900/40 px-2 py-0.5 text-[10px] font-medium text-red-400 hover:bg-red-900/60 transition disabled:opacity-50"
                >
                  解聘
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Available for hire */}
      <div>
        <h3 className="mb-2 text-xs font-semibold text-slate-440 uppercase tracking-wider">
          📋 可聘用人員 ({filteredAvailable.length})
        </h3>
        {filteredAvailable.length === 0 ? (
          <p className="text-[11px] text-slate-600 py-2">目前無可聘用人員</p>
        ) : (
          <div className="space-y-1.5">
            {filteredAvailable.map((agent) => (
              <div
                key={agent.id}
                className="flex items-center gap-2 rounded-lg border border-slate-700/40 bg-slate-800/40 px-3 py-2 hover:bg-slate-800/60 transition"
              >
                <span className="text-base">{agent.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-medium text-slate-200">
                      {agent.display_name}
                    </span>
                    <span className={`rounded px-1 py-0.5 text-[9px] ${tierColors[agent.tier] ?? 'text-slate-400 bg-slate-800'}`}>
                      {tierLabels[agent.tier] ?? agent.tier}
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500 truncate">{agent.description}</p>
                </div>
                <button
                  onClick={() => hire(agent)}
                  disabled={loading}
                  className="shrink-0 rounded bg-emerald-900/50 px-2.5 py-1 text-[10px] font-medium text-emerald-400 hover:bg-emerald-900/70 transition disabled:opacity-50"
                >
                  聘用
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Skills registry */}
      <div>
        <h3 className="mb-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          🔧 技能模組 ({skills.length})
        </h3>
        <div className="grid grid-cols-2 gap-1">
          {skills.map((skill) => (
            <div key={skill.skill_id} className="rounded border border-slate-700/30 bg-slate-800/30 px-2 py-1.5">
              <div className="text-[10px] font-medium text-slate-300">{skill.display_name}</div>
              <div className="text-[9px] text-slate-600">v{skill.version}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
