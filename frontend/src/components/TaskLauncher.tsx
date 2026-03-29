/**
 * TaskLauncher — 任務啟動面板。
 *
 * 取代裸指令輸入，提供視覺化的任務選擇 + 風機選擇 + 一鍵執行。
 * 進階使用者可展開指令輸入框手動操作。
 */

import { useState, useEffect } from 'react'
import { useTheme } from '../themes'

interface TaskLauncherProps {
  onExecute: (command: string, parameters: Record<string, string>) => void
  disabled?: boolean
}

interface TaskDef {
  id: string
  label: string
  icon: string
  description: string
  category: 'diagnose' | 'data' | 'ai' | 'research'
  paramType: 'turbine' | 'topic' | 'folder' | 'none'
}

const TASKS: TaskDef[] = [
  { id: 'diagnose', label: '故障診斷', icon: '🔧', description: '完整故障分析流程', category: 'diagnose', paramType: 'turbine' },
  { id: 'monthly-review', label: '月度健康評估', icon: '📋', description: 'SCADA + 警報 + 運維月報', category: 'diagnose', paramType: 'turbine' },
  { id: 'train-nbm', label: 'NBM 訓練', icon: '📈', description: '功率曲線模型訓練', category: 'ai', paramType: 'turbine' },
  { id: 'predict-rul', label: 'RUL 預測', icon: '⏱️', description: '剩餘壽命預測', category: 'ai', paramType: 'turbine' },
  { id: 'data:load', label: '資料載入', icon: '📂', description: '載入 + 品質檢查', category: 'data', paramType: 'turbine' },
  { id: 'data:clean', label: '資料清洗', icon: '🧹', description: '去重 + 插值 + 異常過濾', category: 'data', paramType: 'turbine' },
  { id: 'ai:train', label: 'ML 訓練', icon: '🧠', description: '平行訓練三個模型', category: 'ai', paramType: 'turbine' },
  { id: 'ai:evaluate', label: '模型評估', icon: '📊', description: '殘差 + 混淆矩陣', category: 'ai', paramType: 'turbine' },
  { id: 'lit-search', label: '文獻搜索', icon: '📖', description: '系統性文獻回顧', category: 'research', paramType: 'topic' },
]

const CATEGORY_LABELS: Record<string, string> = {
  diagnose: '診斷',
  data: '資料',
  ai: 'AI / ML',
  research: '研究',
}

const FALLBACK_TURBINES = ['Kelmarsh_1', 'Kelmarsh_2', 'Kelmarsh_3', 'Kelmarsh_4', 'Kelmarsh_5', 'Kelmarsh_6']

export default function TaskLauncher({ onExecute, disabled = false }: TaskLauncherProps) {
  const { theme } = useTheme()
  const [selectedTask, setSelectedTask] = useState<string | null>(null)
  const [turbines, setTurbines] = useState<string[]>(FALLBACK_TURBINES)
  const [selectedTurbine, setSelectedTurbine] = useState(FALLBACK_TURBINES[0])
  const [topicInput, setTopicInput] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advancedInput, setAdvancedInput] = useState('')

  useEffect(() => {
    fetch('http://localhost:8000/api/scada/turbines')
      .then((res) => res.json())
      .then((data) => {
        if (data.turbines?.length > 0) {
          setTurbines(data.turbines)
          setSelectedTurbine(data.turbines[0])
        }
      })
      .catch(() => { /* fallback */ })
  }, [])

  const task = TASKS.find((t) => t.id === selectedTask)

  const handleExecute = () => {
    if (!task || disabled) return
    const params: Record<string, string> = {}
    if (task.paramType === 'turbine') params.turbine_id = selectedTurbine
    if (task.paramType === 'topic') params.topic = topicInput || 'wind turbine fault diagnosis'
    onExecute(task.id, params)
  }

  const handleAdvancedSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!advancedInput.trim()) return
    const parts = advancedInput.trim().split(/\s+/)
    const cmd = parts[0].replace(/^\//, '')
    const paramValue = parts.slice(1).join(' ')
    const params: Record<string, string> = {}
    const turbineCmds = ['diagnose', 'monthly-review', 'train-nbm', 'predict-rul', 'data:load', 'data:clean', 'ai:train', 'ai:evaluate']
    if (turbineCmds.includes(cmd)) params.turbine_id = paramValue || selectedTurbine
    else if (cmd === 'lit-search') params.topic = paramValue || 'wind turbine fault diagnosis'
    else if (cmd === 'data:folder' || cmd === 'rag:ingest' || cmd === 'project:onboard') params.folder_path = paramValue
    else if (cmd === 'rag:search') params.query = paramValue
    else if (cmd === 'bosscall') params.target = paramValue
    onExecute(cmd, params)
    setAdvancedInput('')
  }

  const categoryColor = (cat: string) => {
    const map: Record<string, string> = {
      diagnose: theme.tiers.engineering.primary,
      data: theme.tiers.data.primary,
      ai: theme.tiers['ai-ml'].primary,
      research: theme.tiers.research.primary,
    }
    return map[cat] ?? theme.global.accent
  }

  // 按類別分組
  const grouped = ['diagnose', 'data', 'ai', 'research'].map((cat) => ({
    category: cat,
    label: CATEGORY_LABELS[cat],
    tasks: TASKS.filter((t) => t.category === cat),
  }))

  return (
    <div className="space-y-3">
      {/* ── 任務選擇 Grid ── */}
      <div className="space-y-2">
        {grouped.map(({ category, label, tasks }) => (
          <div key={category}>
            <div
              className="text-[9px] uppercase tracking-wider font-medium mb-1 px-1"
              style={{ color: categoryColor(category) + 'aa' }}
            >
              {label}
            </div>
            <div className="grid grid-cols-4 gap-1.5">
              {tasks.map((t) => {
                const isSelected = selectedTask === t.id
                const color = categoryColor(t.category)
                return (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTask(isSelected ? null : t.id)}
                    disabled={disabled}
                    className="flex flex-col items-center gap-1 rounded-lg border p-2 transition-all duration-200 hover:brightness-110 disabled:opacity-40"
                    style={{
                      borderColor: isSelected ? color : theme.global.border + '60',
                      backgroundColor: isSelected ? color + '15' : 'transparent',
                    }}
                  >
                    <span className="text-base">{t.icon}</span>
                    <span
                      className="text-[10px] font-medium leading-tight"
                      style={{ color: isSelected ? color : theme.global.textSecondary }}
                    >
                      {t.label}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* ── 參數 + 執行 ── */}
      {task && (
        <div
          className="flex items-center gap-2 rounded-lg border p-2"
          style={{ borderColor: categoryColor(task.category) + '40', backgroundColor: categoryColor(task.category) + '08' }}
        >
          <span className="text-sm">{task.icon}</span>
          <span className="text-xs font-medium" style={{ color: categoryColor(task.category) }}>{task.label}</span>
          <span className="text-[10px]" style={{ color: theme.global.textMuted }}>{task.description}</span>

          <div className="ml-auto flex items-center gap-2">
            {task.paramType === 'turbine' && (
              <select
                value={selectedTurbine}
                onChange={(e) => setSelectedTurbine(e.target.value)}
                className="rounded border px-2 py-1 text-xs outline-none"
                style={{
                  borderColor: theme.global.border,
                  backgroundColor: theme.global.panelBg,
                  color: theme.global.textPrimary,
                }}
              >
                {turbines.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            )}
            {task.paramType === 'topic' && (
              <input
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder="搜索主題..."
                className="rounded border px-2 py-1 text-xs outline-none w-40"
                style={{
                  borderColor: theme.global.border,
                  backgroundColor: theme.global.panelBg,
                  color: theme.global.textPrimary,
                }}
              />
            )}
            <button
              onClick={handleExecute}
              disabled={disabled}
              className="rounded-lg px-4 py-1.5 text-xs font-medium text-white transition-colors hover:brightness-110 disabled:opacity-40"
              style={{ backgroundColor: categoryColor(task.category) }}
            >
              ▶ 執行
            </button>
          </div>
        </div>
      )}

      {/* ── 進階指令（收合） ── */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-[10px] transition-colors hover:brightness-125"
          style={{ color: theme.global.textMuted }}
        >
          <svg className={`h-3 w-3 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          進階指令輸入
        </button>
        {showAdvanced && (
          <form onSubmit={handleAdvancedSubmit} className="flex items-center gap-2 mt-1">
            <input
              value={advancedInput}
              onChange={(e) => setAdvancedInput(e.target.value)}
              placeholder="/diagnose Kelmarsh_1 或 /bosscall 故障診斷師"
              className="flex-1 rounded border px-3 py-1.5 text-xs outline-none"
              style={{
                borderColor: theme.global.border,
                backgroundColor: theme.global.panelBg,
                color: theme.global.textPrimary,
              }}
            />
            <button
              type="submit"
              disabled={disabled || !advancedInput.trim()}
              className="rounded px-3 py-1.5 text-xs font-medium text-white disabled:opacity-40"
              style={{ backgroundColor: theme.global.accent }}
            >
              送出
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
