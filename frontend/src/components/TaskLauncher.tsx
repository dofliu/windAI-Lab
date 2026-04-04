/**
 * TaskLauncher — 任務啟動面板（精簡版）。
 *
 * 預設為單行精簡模式：顯示當前選中的任務 + 參數 + 執行按鈕。
 * 點擊展開按鈕後，向上滑出完整的任務選擇面板。
 */

import { useState, useEffect, useRef } from 'react'
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
  { id: 'health-check', label: '健康檢查', icon: '🩺', description: '異常偵測 + 健康分數 + 報告', category: 'diagnose', paramType: 'turbine' },
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
  const [selectedTask, setSelectedTask] = useState<string>('data:clean')
  const [turbines, setTurbines] = useState<string[]>(FALLBACK_TURBINES)
  const [selectedTurbine, setSelectedTurbine] = useState(FALLBACK_TURBINES[0])
  const [topicInput, setTopicInput] = useState('')
  const [expanded, setExpanded] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advancedInput, setAdvancedInput] = useState('')
  const panelRef = useRef<HTMLDivElement>(null)

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

  // 點擊外部時收合面板
  useEffect(() => {
    if (!expanded) return
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setExpanded(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [expanded])

  const task = TASKS.find((t) => t.id === selectedTask)

  const handleExecute = () => {
    if (!task || disabled) return
    const params: Record<string, string> = {}
    if (task.paramType === 'turbine') params.turbine_id = selectedTurbine
    if (task.paramType === 'topic') params.topic = topicInput || 'wind turbine fault diagnosis'
    onExecute(task.id, params)
    setExpanded(false)
  }

  const handleAdvancedSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!advancedInput.trim()) return
    const parts = advancedInput.trim().split(/\s+/)
    const cmd = parts[0].replace(/^\//, '')
    const paramValue = parts.slice(1).join(' ')
    const params: Record<string, string> = {}
    const turbineCmds = ['diagnose', 'monthly-review', 'health-check', 'train-nbm', 'predict-rul', 'data:load', 'data:clean', 'ai:train', 'ai:evaluate']
    if (turbineCmds.includes(cmd)) params.turbine_id = paramValue || selectedTurbine
    else if (cmd === 'lit-search') params.topic = paramValue || 'wind turbine fault diagnosis'
    else if (cmd === 'data:folder' || cmd === 'rag:ingest' || cmd === 'project:onboard') params.folder_path = paramValue
    else if (cmd === 'rag:search') params.query = paramValue
    else if (cmd === 'bosscall') params.target = paramValue
    onExecute(cmd, params)
    setAdvancedInput('')
    setExpanded(false)
  }

  const handleSelectTask = (taskId: string) => {
    setSelectedTask(taskId)
    setExpanded(false)
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

  const grouped = ['diagnose', 'data', 'ai', 'research'].map((cat) => ({
    category: cat,
    label: CATEGORY_LABELS[cat],
    tasks: TASKS.filter((t) => t.category === cat),
  }))

  const accentColor = task ? categoryColor(task.category) : theme.global.accent

  return (
    <div ref={panelRef} className="relative">
      {/* ── 展開的任務選擇面板（向上滑出） ── */}
      <div
        className="absolute bottom-full left-0 right-0 overflow-hidden transition-all duration-300 ease-out"
        style={{
          maxHeight: expanded ? 420 : 0,
          opacity: expanded ? 1 : 0,
        }}
      >
        <div
          className="rounded-t-xl border border-b-0 p-3 shadow-lg backdrop-blur-md space-y-2.5"
          style={{
            borderColor: theme.global.border,
            backgroundColor: theme.global.panelBg + 'f0',
          }}
        >
          {/* 任務 Grid */}
          {grouped.map(({ category, label, tasks }) => (
            <div key={category}>
              <div
                className="text-[9px] uppercase tracking-wider font-medium mb-1 px-0.5"
                style={{ color: categoryColor(category) + 'aa' }}
              >
                {label}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {tasks.map((t) => {
                  const isSelected = selectedTask === t.id
                  const color = categoryColor(t.category)
                  return (
                    <button
                      key={t.id}
                      onClick={() => handleSelectTask(t.id)}
                      disabled={disabled}
                      className="flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 transition-all duration-200 hover:brightness-110 disabled:opacity-40"
                      style={{
                        borderColor: isSelected ? color : theme.global.border + '60',
                        backgroundColor: isSelected ? color + '18' : 'transparent',
                      }}
                    >
                      <span className="text-sm">{t.icon}</span>
                      <div className="text-left">
                        <div
                          className="text-[10px] font-medium leading-tight"
                          style={{ color: isSelected ? color : theme.global.textSecondary }}
                        >
                          {t.label}
                        </div>
                        <div className="text-[8px]" style={{ color: theme.global.textMuted }}>
                          {t.description}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}

          {/* 進階指令 */}
          <div className="pt-1 border-t" style={{ borderColor: theme.global.border + '40' }}>
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
              <form onSubmit={handleAdvancedSubmit} className="flex items-center gap-2 mt-1.5">
                <input
                  value={advancedInput}
                  onChange={(e) => setAdvancedInput(e.target.value)}
                  placeholder="/diagnose Kelmarsh_1 或 /bosscall 故障診斷師"
                  className="flex-1 rounded border px-3 py-1.5 text-xs outline-none"
                  style={{
                    borderColor: theme.global.border,
                    backgroundColor: theme.global.pageBg,
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
      </div>

      {/* ── 精簡底部列 ── */}
      <div className="flex items-center gap-2">
        {/* 展開/收合按鈕 */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 rounded-lg border px-2 py-1.5 transition-all hover:brightness-110"
          style={{
            borderColor: expanded ? accentColor + '60' : theme.global.border + '60',
            backgroundColor: expanded ? accentColor + '10' : 'transparent',
            color: expanded ? accentColor : theme.global.textMuted,
          }}
          title={expanded ? '收合任務面板' : '選擇任務'}
        >
          <svg
            className={`h-3.5 w-3.5 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
          </svg>
        </button>

        {/* 當前任務資訊 */}
        {task && (
          <>
            <span className="text-sm">{task.icon}</span>
            <span className="text-xs font-medium" style={{ color: accentColor }}>
              {task.label}
            </span>
            <span className="text-[10px] hidden sm:inline" style={{ color: theme.global.textMuted }}>
              {task.description}
            </span>
          </>
        )}

        {/* 參數選擇 + 執行 */}
        <div className="ml-auto flex items-center gap-2">
          {task?.paramType === 'turbine' && (
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
          {task?.paramType === 'topic' && (
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
            disabled={disabled || !task}
            className="rounded-lg px-4 py-1.5 text-xs font-medium text-white transition-colors hover:brightness-110 disabled:opacity-40"
            style={{ backgroundColor: accentColor }}
          >
            ▶ 執行
          </button>
        </div>
      </div>
    </div>
  )
}
