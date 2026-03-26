import { useEffect, useRef, useState } from 'react'
import { WorkLog } from '../types/agent'
import { useTheme } from '../themes'

const filterLabels: Record<string, string> = {
  all: '全部',
  info: '資訊',
  success: '完成',
  warning: '警告',
  error: '錯誤',
}

interface WorkLogPanelProps {
  logs: WorkLog[]
}

export default function WorkLogPanel({ logs }: WorkLogPanelProps) {
  const { theme } = useTheme()
  const scrollRef = useRef<HTMLDivElement>(null)
  const [filter, setFilter] = useState<string>('all')

  const filteredLogs = filter === 'all' ? logs : logs.filter((l) => l.type === filter)

  const typeColors: Record<string, { dot: string; border: string }> = {
    info:    { dot: theme.global.textSecondary, border: theme.global.border },
    success: { dot: theme.statuses.working.dot, border: theme.statuses.working.bg },
    warning: { dot: theme.statuses.waiting.dot, border: theme.statuses.waiting.bg },
    error:   { dot: theme.statuses.error.dot,   border: theme.statuses.error.bg },
  }

  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [filteredLogs.length])

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 border-b px-4 py-2"
        style={{ borderColor: theme.global.border }}
      >
        <h3 className="mr-2 text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
          工作日誌
        </h3>
        {Object.entries(filterLabels).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className="rounded-md px-2 py-0.5 text-xs transition-colors"
            style={{
              backgroundColor: filter === key ? theme.global.accent : 'transparent',
              color: filter === key ? '#fff' : theme.global.textSecondary,
            }}
          >
            {label}
          </button>
        ))}
        <span className="ml-auto text-xs" style={{ color: theme.global.textMuted }}>
          {filteredLogs.length} 筆紀錄
        </span>
      </div>

      {/* Log Entries */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2">
        {filteredLogs.length === 0 ? (
          <p className="py-4 text-center text-xs" style={{ color: theme.global.textMuted }}>
            尚無符合條件的日誌
          </p>
        ) : (
          <div className="space-y-0.5">
            {filteredLogs.map((log) => {
              const tc = typeColors[log.type] ?? typeColors.info
              return (
                <div
                  key={log.id}
                  className="rounded px-2 py-1 border-l-2"
                  style={{ borderColor: tc.border }}
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: tc.dot }}
                    />
                    <span className="text-xs" style={{ color: theme.global.textMuted }}>
                      {log.timestamp.toLocaleTimeString('zh-TW', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                    <span className="text-xs font-medium" style={{ color: theme.global.accent }}>
                      {log.agentName}
                    </span>
                  </div>
                  <p className="ml-5 text-xs" style={{ color: theme.global.textSecondary }}>
                    {log.message}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
