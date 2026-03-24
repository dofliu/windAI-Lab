import { useEffect, useRef, useState } from 'react'
import { WorkLog } from '../types/agent'

const typeStyles: Record<WorkLog['type'], { border: string; dot: string }> = {
  info: { border: 'border-slate-600', dot: 'bg-slate-400' },
  success: { border: 'border-emerald-700', dot: 'bg-emerald-400' },
  warning: { border: 'border-amber-700', dot: 'bg-amber-400' },
  error: { border: 'border-red-700', dot: 'bg-red-400' },
}

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
  const scrollRef = useRef<HTMLDivElement>(null)
  const [filter, setFilter] = useState<string>('all')

  const filteredLogs = filter === 'all' ? logs : logs.filter((l) => l.type === filter)

  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }, [filteredLogs.length])

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-slate-700/50 px-4 py-2">
        <h3 className="mr-2 text-sm font-semibold text-slate-300">
          工作日誌
        </h3>
        {Object.entries(filterLabels).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`rounded-md px-2 py-0.5 text-xs transition-colors ${
              filter === key
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-600">
          {filteredLogs.length} 筆紀錄
        </span>
      </div>

      {/* Log Entries */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2">
        {filteredLogs.length === 0 ? (
          <p className="py-4 text-center text-xs text-slate-600">
            尚無符合條件的日誌
          </p>
        ) : (
          <div className="space-y-0.5">
            {filteredLogs.map((log) => {
              const style = typeStyles[log.type]
              return (
                <div key={log.id} className={`log-entry ${style.border}`}>
                  <div className="flex items-center gap-2">
                    <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} />
                    <span className="text-xs text-slate-500">
                      {log.timestamp.toLocaleTimeString('zh-TW', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </span>
                    <span className="text-xs font-medium text-indigo-400">
                      {log.agentName}
                    </span>
                  </div>
                  <p className="ml-5 text-xs text-slate-300">{log.message}</p>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
