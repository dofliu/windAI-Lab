import { useState, useRef } from 'react'

interface CommandBarProps {
  onExecute: (command: string, parameters: Record<string, string>) => void
  disabled?: boolean
}

const COMMANDS = [
  { name: 'diagnose-real', label: '/diagnose-real', description: '真實資料故障診斷', paramHint: '風機 ID (如 WT-01)' },
  { name: 'diagnose', label: '/diagnose', description: '風機故障診斷 (模擬)', paramHint: '風機 ID (如 WT-07)' },
  { name: 'lit-search', label: '/lit-search', description: '系統性文獻搜索', paramHint: '搜索主題' },
]

export default function CommandBar({ onExecute, disabled }: CommandBarProps) {
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
      if ((cmdName === 'diagnose' || cmdName === 'diagnose-real') && paramValue) {
        params.turbine_id = paramValue
      } else if (cmdName === 'lit-search' && paramValue) {
        params.topic = paramValue
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
                  <span className="font-mono text-cyan-400">{cmd.label}</span>
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
