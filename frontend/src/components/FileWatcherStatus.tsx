import { useState, useEffect, useCallback } from 'react'

interface FileEvent {
  filename: string
  path: string
  turbine_id: string | null
  size_display: string
  total_records: number
  detected_fields: Record<string, string> | null
  analysis_summary: {
    numeric_columns: number
    target_column: string | null
    top_features: string[]
    anomaly_columns: number
  } | null
  error_message: string | null
}

interface Props {
  /** WebSocket 推送的檔案事件 */
  fileEvents: FileEvent[]
}

export default function FileWatcherStatus({ fileEvents }: Props) {
  const [isRunning, setIsRunning] = useState(false)
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [expanded, setExpanded] = useState(false)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/api/file-watcher/status')
      const data = await res.json()
      setIsRunning(data.running ?? false)
      setStatus(data)
    } catch {
      setIsRunning(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const timer = setInterval(fetchStatus, 10000)
    return () => clearInterval(timer)
  }, [fetchStatus])

  const toggle = async () => {
    try {
      const endpoint = isRunning ? 'stop' : 'start'
      await fetch(`http://localhost:8000/api/file-watcher/${endpoint}`, { method: 'POST' })
      await fetchStatus()
    } catch {
      // ignore
    }
  }

  const [scanning, setScanning] = useState(false)
  const forceScan = async () => {
    setScanning(true)
    try {
      await fetch('http://localhost:8000/api/file-watcher/scan', { method: 'POST' })
      await fetchStatus()
    } catch {
      // ignore
    }
    setScanning(false)
  }

  const recentEvents = fileEvents.slice(-5).reverse()

  return (
    <div className="space-y-2">
      {/* Compact status bar */}
      <div
        className="flex items-center gap-2 rounded-lg bg-slate-800/60 px-3 py-2 cursor-pointer hover:bg-slate-800/80 transition"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Status indicator */}
        <div className={`h-2 w-2 rounded-full ${isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
        <span className="text-xs font-medium text-slate-300">
          {isRunning ? '📁 檔案監控中' : '📁 監控已暫停'}
        </span>

        {/* Stats */}
        {status && (
          <span className="text-[10px] text-slate-500 ml-1">
            ({(status.known_files as number) ?? 0} 檔案 · {(status.processed_count as number) ?? 0} 已處理)
          </span>
        )}

        {/* New file notification badge */}
        {recentEvents.length > 0 && (
          <span className="ml-auto flex items-center gap-1 rounded-full bg-cyan-600/30 px-2 py-0.5 text-[10px] text-cyan-300">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
            {recentEvents.length} 新
          </span>
        )}

        {/* Force scan button */}
        <button
          onClick={(e) => { e.stopPropagation(); forceScan() }}
          className="rounded bg-cyan-900/40 px-2 py-0.5 text-[10px] font-medium text-cyan-400 hover:bg-cyan-900/60 transition"
          disabled={scanning}
        >
          {scanning ? '掃描中...' : '🔍 掃描'}
        </button>

        {/* Toggle button */}
        <button
          onClick={(e) => { e.stopPropagation(); toggle() }}
          className={`rounded px-2 py-0.5 text-[10px] font-medium transition ${
            isRunning
              ? 'bg-red-900/40 text-red-400 hover:bg-red-900/60'
              : 'bg-emerald-900/40 text-emerald-400 hover:bg-emerald-900/60'
          }`}
        >
          {isRunning ? '暫停' : '啟動'}
        </button>

        {/* Expand icon */}
        <span className={`text-xs text-slate-600 transition-transform ${expanded ? 'rotate-180' : ''}`}>
          ▼
        </span>
      </div>

      {/* Expanded: recent file events */}
      {expanded && (
        <div className="space-y-1.5 pl-2">
          {recentEvents.length === 0 ? (
            <p className="text-[10px] text-slate-600 py-2">尚未偵測到新檔案。將資料放入 data/raw/ 目錄即可。</p>
          ) : (
            recentEvents.map((event, i) => (
              <div key={i} className="rounded-lg border border-slate-700/50 bg-slate-800/40 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{event.error_message ? '❌' : '✅'}</span>
                  <span className="text-xs font-medium text-slate-200 truncate" title={event.filename}>
                    {event.filename}
                  </span>
                  <span className="ml-auto text-[10px] text-slate-500">{event.size_display}</span>
                </div>

                {event.detected_fields && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {Object.entries(event.detected_fields).slice(0, 6).map(([key, col]) => (
                      <span
                        key={key}
                        className="rounded bg-slate-700/60 px-1.5 py-0.5 text-[9px] text-slate-400"
                        title={`${key} → ${col}`}
                      >
                        {key}
                      </span>
                    ))}
                  </div>
                )}

                {event.analysis_summary && (
                  <div className="mt-1 text-[10px] text-slate-500">
                    {event.total_records.toLocaleString()} 筆 ·
                    {event.analysis_summary.numeric_columns} 欄位 ·
                    Top: {event.analysis_summary.top_features.slice(0, 2).join(', ')}
                  </div>
                )}

                {event.error_message && (
                  <div className="mt-1 text-[10px] text-red-400 truncate">{event.error_message}</div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
