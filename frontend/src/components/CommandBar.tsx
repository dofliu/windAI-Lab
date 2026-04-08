import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

interface CommandBarProps {
  onExecute: (command: string, parameters: Record<string, string>) => void
  disabled?: boolean
}

/** 需要帶 turbine_id 參數的指令 */
const TURBINE_COMMANDS = ['diagnose', 'health-check', 'train-nbm', 'predict-rul', 'data:load', 'data:clean', 'ai:train', 'ai:evaluate']

const COMMANDS = [
  // ── 後端 Workflow 指令（統一路由） ──
  { name: 'diagnose', label: '/diagnose', description: '故障診斷（完整流程）', paramHint: '風機 ID', category: 'diagnose' },
  { name: 'health-check', label: '/health-check', description: '異常偵測 + 健康分數 + 報告', paramHint: '風機 ID', category: 'diagnose' },
  { name: 'train-nbm', label: '/train-nbm', description: 'NBM 功率曲線訓練', paramHint: '風機 ID', category: 'ai' },
  { name: 'predict-rul', label: '/predict-rul', description: 'RUL 壽命預測', paramHint: '風機 ID', category: 'ai' },
  { name: 'data:load', label: '/data:load', description: '資料載入 + 品質檢查', paramHint: '風機 ID', category: 'data' },
  { name: 'data:clean', label: '/data:clean', description: '資料清洗 + 異常過濾', paramHint: '風機 ID', category: 'data' },
  { name: 'ai:train', label: '/ai:train', description: 'ML 模型訓練（平行）', paramHint: '風機 ID', category: 'ai' },
  { name: 'ai:evaluate', label: '/ai:evaluate', description: '模型效能評估', paramHint: '風機 ID', category: 'ai' },
  { name: 'lit-search', label: '/lit-search', description: '系統性文獻搜索', paramHint: '搜索主題', category: 'research' },
  // ── 特殊指令 ──
  { name: 'project:onboard', label: '/project:onboard', description: '專案一鍵上線（LLM 分類+RAG+資料）', paramHint: '資料夾路徑', category: 'data' },
  { name: 'data:folder', label: '/data:folder', description: '資料夾批次載入', paramHint: '資料夾路徑', category: 'data' },
  { name: 'rag:ingest', label: '/rag:ingest', description: 'RAG 資料夾嵌入', paramHint: '資料夾路徑', category: 'research' },
  { name: 'rag:search', label: '/rag:search', description: 'RAG 語意搜尋', paramHint: '查詢關鍵字', category: 'research' },
  // ── 辦公室互動 ──
  { name: 'bosscall', label: '/bosscall', description: '小房間召喚', paramHint: '員工名稱', category: 'fun' },
  { name: 'teatime', label: '/teatime', description: '茶水間休息', paramHint: '', category: 'fun' },
  { name: 'gametime', label: '/gametime', description: '遊戲間打電動', paramHint: '', category: 'fun' },
]

const QUICK_ACTIONS = [
  { name: 'diagnose', label: '故障診斷', icon: '🔧', category: 'diagnose' },
  { name: 'train-nbm', label: 'NBM 訓練', icon: '📈', category: 'ai' },
  { name: 'predict-rul', label: 'RUL 預測', icon: '⏱️', category: 'ai' },
  { name: 'data:load', label: '資料載入', icon: '📂', category: 'data' },
  { name: 'ai:train', label: 'ML 訓練', icon: '🧠', category: 'ai' },
  { name: 'project:onboard', label: '專案上線', icon: '🚀', category: 'data' },
  { name: 'rag:ingest', label: 'RAG 嵌入', icon: '📚', category: 'research' },
]

const FALLBACK_TURBINES = ['Kelmarsh_1', 'Kelmarsh_2', 'Kelmarsh_3', 'Kelmarsh_4', 'Kelmarsh_5', 'Kelmarsh_6']

export default function CommandBar({ onExecute, disabled = false }: CommandBarProps) {
  const { theme } = useTheme()
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [turbines, setTurbines] = useState<string[]>(FALLBACK_TURBINES)
  const [selectedTurbine, setSelectedTurbine] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // 從後端取得可用風機列表
  useEffect(() => {
    fetch(`${API_BASE}/scada/turbines`)
      .then((res) => res.json())
      .then((data) => {
        if (data.turbines && data.turbines.length > 0) {
          setTurbines(data.turbines)
          setSelectedTurbine(data.turbines[0])
        }
      })
      .catch(() => {
        // 後端未啟動時用 fallback
        setSelectedTurbine(FALLBACK_TURBINES[0])
      })
  }, [])

  const categoryColors: Record<string, string> = {
    data: theme.tiers.data.primary,
    ai: theme.tiers['ai-ml'].primary,
    diagnose: theme.tiers.engineering.primary,
    research: theme.tiers.research.primary,
    simu: theme.global.textMuted,
    fun: theme.statuses.waiting.dot,
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || disabled) return

    const parts = input.trim().split(/\s+/)
    const cmdName = parts[0].replace(/^\//, '')
    const paramValue = parts.slice(1).join(' ')

    const cmd = COMMANDS.find(c => c.name === cmdName)
    if (cmd) {
      const params: Record<string, string> = {}
      if (TURBINE_COMMANDS.includes(cmdName)) {
        params.turbine_id = paramValue || selectedTurbine
      } else if (cmdName === 'data:folder' && paramValue) {
        params.folder_path = paramValue
      } else if (cmdName === 'lit-search' && paramValue) {
        params.topic = paramValue
      } else if (cmdName === 'project:onboard' && paramValue) {
        params.folder_path = paramValue
      } else if (cmdName === 'rag:ingest' && paramValue) {
        params.folder_path = paramValue
      } else if (cmdName === 'rag:search' && paramValue) {
        params.query = paramValue
      } else if (cmdName === 'bosscall' && paramValue) {
        params.target = paramValue
      } else if (cmdName.startsWith('simu-')) {
        params.turbine_id = paramValue || selectedTurbine
      }
      onExecute(cmdName, params)
      setInput('')
      setShowSuggestions(false)
    }
  }

  const handleQuickAction = (cmdName: string) => {
    if (disabled) return
    // 需要路徑參數的指令：填入輸入框而非直接執行
    if (cmdName === 'project:onboard' || cmdName === 'rag:ingest') {
      setInput(`/${cmdName} `)
      inputRef.current?.focus()
      return
    }
    const params: Record<string, string> = {}
    if (TURBINE_COMMANDS.includes(cmdName)) {
      params.turbine_id = selectedTurbine
    }
    onExecute(cmdName, params)
  }

  const handleSuggestionClick = (cmdName: string) => {
    setInput(`/${cmdName} `)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }

  const filteredCommands = input.startsWith('/')
    ? COMMANDS.filter(c => `/${c.name}`.startsWith(input.split(/\s/)[0]))
    : COMMANDS

  return (
    <div className="space-y-2">
      {/* ── 快速操作列 ── */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* 風機選擇器 */}
        <div className="flex items-center gap-1.5">
          <span className="text-xs" style={{ color: theme.global.textMuted }}>風機</span>
          <select
            value={selectedTurbine}
            onChange={(e) => setSelectedTurbine(e.target.value)}
            disabled={disabled}
            className="rounded-md border px-2 py-1 text-xs outline-none transition-colors disabled:opacity-50"
            style={{
              borderColor: theme.global.border,
              backgroundColor: theme.global.panelBg,
              color: theme.global.textPrimary,
            }}
          >
            {turbines.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        <div
          className="mx-1 h-5 w-px"
          style={{ backgroundColor: theme.global.border }}
        />

        {/* 快捷按鈕 */}
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.name}
            type="button"
            onClick={() => handleQuickAction(action.name)}
            disabled={disabled}
            className="flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-medium transition-all hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              borderColor: categoryColors[action.category] + '40',
              backgroundColor: categoryColors[action.category] + '15',
              color: categoryColors[action.category],
            }}
            title={`${action.label}（${selectedTurbine}）`}
          >
            <span>{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>

      {/* ── 指令輸入列（保留進階手動輸入） ── */}
      <div className="relative">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <div className="relative flex-1">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                setShowSuggestions(e.target.value.startsWith('/'))
              }}
              onFocus={() => { if (input.startsWith('/')) setShowSuggestions(true) }}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
              placeholder={`輸入指令（如 /diagnose ${selectedTurbine}）或使用上方快捷鍵`}
              disabled={disabled}
              className="w-full rounded-lg border px-4 py-2 text-sm outline-none transition-colors disabled:opacity-50"
              style={{
                borderColor: theme.global.border,
                backgroundColor: theme.global.panelBg,
                color: theme.global.textPrimary,
              }}
            />

            {showSuggestions && filteredCommands.length > 0 && (
              <div
                className="absolute bottom-full left-0 mb-1 w-full rounded-lg border py-1 shadow-xl z-50"
                style={{ borderColor: theme.global.border, backgroundColor: theme.global.panelBg }}
              >
                {filteredCommands.map((cmd) => (
                  <button
                    key={cmd.name}
                    type="button"
                    onMouseDown={() => handleSuggestionClick(cmd.name)}
                    className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm hover:opacity-80"
                  >
                    <span className="font-mono" style={{ color: categoryColors[cmd.category] ?? theme.global.accent }}>
                      {cmd.label}
                    </span>
                    <span style={{ color: theme.global.textSecondary }}>{cmd.description}</span>
                    <span className="ml-auto text-xs" style={{ color: theme.global.textMuted }}>{cmd.paramHint}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={disabled || !input.trim()}
            className="rounded-lg px-5 py-2 text-sm font-medium text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            style={{ backgroundColor: theme.global.accent }}
          >
            執行
          </button>
        </form>
      </div>
    </div>
  )
}
