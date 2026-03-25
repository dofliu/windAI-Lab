import { useState, useRef } from 'react'

interface CommandBarProps {
  onExecute: (command: string, parameters: Record<string, string>) => void
  disabled?: boolean
}

const COMMANDS = [
  // 資料操作
  { name: 'data:load', label: '/data:load', description: '智慧載入 SCADA 資料', paramHint: '風機 ID', category: 'data' },
  { name: 'data:clean', label: '/data:clean', description: '自動資料清洗', paramHint: '風機 ID', category: 'data' },
  // 模型操作
  { name: 'ai:train', label: '/ai:train', description: '端到端 ML 模型訓練', paramHint: '風機 ID', category: 'ai' },
  { name: 'ai:evaluate', label: '/ai:evaluate', description: '模型效能評估', paramHint: '風機 ID', category: 'ai' },
  // 診斷
  { name: 'diagnose-real', label: '/diagnose-real', description: '真實資料故障診斷', paramHint: '風機 ID', category: 'diagnose' },
  { name: 'diagnose', label: '/diagnose', description: '風機故障診斷 (模擬)', paramHint: '風機 ID', category: 'diagnose' },
  // 研究
  { name: 'lit-search', label: '/lit-search', description: '系統性文獻搜索', paramHint: '搜索主題', category: 'research' },
  // 辦公室互動
  { name: 'bosscall', label: '/bosscall', description: '小房間召喚 ❤️', paramHint: '員工名稱', category: 'fun' },
  { name: 'teatime', label: '/teatime', description: '茶水間休息 ☕', paramHint: '', category: 'fun' },
  { name: 'gametime', label: '/gametime', description: '遊戲間打電動 🎮', paramHint: '', category: 'fun' },
]

export default function CommandBar({ onExecute, disabled = false }: CommandBarProps) {
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || disabled) return

    const parts = input.trim().split(/\s+/)
    const cmdName = parts[0].replace(/^\//, '')
    const paramValue = parts.slice(1).join(' ')

    const cmd = COMMANDS.find(c => c.name === cmdName)
    if (cmd) {
      const params: Record<string, string> = {}
      if (['diagnose', 'diagnose-real', 'data:load', 'data:clean', 'ai:train', 'ai:evaluate'].includes(cmdName) && paramValue) {
        params.turbine_id = paramValue
      } else if (cmdName === 'lit-search' && paramValue) {
        params.topic = paramValue
      } else if (cmdName === 'bosscall' && paramValue) {
        params.target = paramValue
      }
      onExecute(cmdName, params)
      setInput('')
      setShowSuggestions(false)
    }
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
            placeholder="輸入指令（如 /diagnose WT-07）"
            disabled={disabled}
            className="w-full rounded-lg border border-slate-600 bg-slate-800 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/30 disabled:opacity-50"
          />

          {/* 指令建議面板 */}
          {showSuggestions && filteredCommands.length > 0 && (
            <div className="absolute bottom-full left-0 mb-1 w-full rounded-lg border border-slate-600 bg-slate-800 py-1 shadow-xl">
              {filteredCommands.map((cmd) => (
                <button
                  key={cmd.name}
                  type="button"
                  onMouseDown={() => handleSuggestionClick(cmd.name)}
                  className="flex w-full items-center gap-3 px-4 py-2 text-left text-sm hover:bg-slate-700/50"
                >
                  <span className={`font-mono ${
                    cmd.category === 'data' ? 'text-emerald-400' :
                    cmd.category === 'ai' ? 'text-purple-400' :
                    cmd.category === 'diagnose' ? 'text-orange-400' :
                    cmd.category === 'research' ? 'text-blue-400' :
                    'text-yellow-400'
                  }`}>{cmd.label}</span>
                  <span className="text-slate-400">{cmd.description}</span>
                  <span className="ml-auto text-xs text-slate-500">{cmd.paramHint}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="rounded-lg bg-cyan-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          執行
        </button>
      </form>
    </div>
  )
}
