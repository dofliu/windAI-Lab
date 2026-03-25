import { useState, useCallback } from 'react'
import { Search, BookOpen, Database } from 'lucide-react'

interface SearchResultItem {
  doc_id: string
  content: string
  relevance: number
  metadata: Record<string, string | number>
}

interface KBStats {
  total_collections: number
  total_documents: number
  collections: { name: string; count: number }[]
}

export default function KnowledgeBasePanel() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [stats, setStats] = useState<KBStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'search' | 'stats'>('search')

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `http://localhost:8000/api/knowledge-base/search?query=${encodeURIComponent(query)}&n_results=10`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.status === 'error') {
        setError(data.detail || '搜尋失敗')
      } else {
        setResults(data.results || [])
      }
    } catch {
      setError('無法連線至後端')
    } finally {
      setLoading(false)
    }
  }, [query])

  const loadStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('http://localhost:8000/api/knowledge-base/stats')
      const data = await res.json()
      if (data.status === 'error') {
        setError(data.detail || '查詢失敗')
      } else {
        setStats(data)
      }
    } catch {
      setError('無法連線至後端')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
          <BookOpen size={12} />
          RAG 知識庫
        </h3>
        <div className="flex gap-1">
          <button
            onClick={() => setActiveView('search')}
            className={`rounded px-2 py-0.5 text-[10px] ${activeView === 'search' ? 'bg-slate-700 text-slate-200' : 'text-slate-500'}`}
          >
            搜尋
          </button>
          <button
            onClick={() => { setActiveView('stats'); loadStats() }}
            className={`rounded px-2 py-0.5 text-[10px] ${activeView === 'stats' ? 'bg-slate-700 text-slate-200' : 'text-slate-500'}`}
          >
            統計
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded bg-red-900/30 px-2 py-1 text-[10px] text-red-400">{error}</div>
      )}

      {/* Search view */}
      {activeView === 'search' && (
        <>
          <div className="flex gap-1.5">
            <div className="relative flex-1">
              <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="輸入搜尋查詢（如：風機故障診斷方法）"
                className="w-full rounded bg-slate-800 py-1.5 pl-7 pr-2 text-[10px] text-slate-200 outline-none ring-1 ring-slate-700 focus:ring-cyan-600"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="rounded bg-cyan-600 px-2.5 text-[10px] font-medium text-white transition hover:bg-cyan-500 disabled:opacity-50"
            >
              {loading ? '...' : '搜尋'}
            </button>
          </div>

          {results.length > 0 && (
            <div className="space-y-2">
              <p className="text-[9px] text-slate-500">找到 {results.length} 筆結果</p>
              {results.map((r) => (
                <div key={r.doc_id} className="rounded bg-slate-800/80 p-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[9px] text-slate-500">{r.doc_id.slice(0, 8)}...</span>
                    <span className={`text-[9px] font-medium ${
                      r.relevance >= 0.8 ? 'text-emerald-400' : r.relevance >= 0.5 ? 'text-amber-400' : 'text-slate-500'
                    }`}>
                      相關度 {(r.relevance * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] leading-relaxed text-slate-300">
                    {r.content}
                  </p>
                  {r.metadata.source && (
                    <p className="mt-1 text-[9px] text-slate-600">
                      來源：{String(r.metadata.source)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {results.length === 0 && !loading && query && (
            <p className="text-center text-[10px] text-slate-600">無搜尋結果（知識庫可能為空）</p>
          )}

          {!query && results.length === 0 && (
            <p className="text-[10px] text-slate-600">輸入關鍵字搜尋風力發電領域知識...</p>
          )}
        </>
      )}

      {/* Stats view */}
      {activeView === 'stats' && stats && (
        <div className="space-y-2">
          <div className="flex gap-3">
            <div className="flex items-center gap-1.5 rounded bg-slate-800/80 px-2 py-1.5">
              <Database size={12} className="text-cyan-400" />
              <div>
                <p className="text-[9px] text-slate-500">集合數</p>
                <p className="text-sm font-bold text-slate-200">{stats.total_collections}</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 rounded bg-slate-800/80 px-2 py-1.5">
              <BookOpen size={12} className="text-violet-400" />
              <div>
                <p className="text-[9px] text-slate-500">文件數</p>
                <p className="text-sm font-bold text-slate-200">{stats.total_documents}</p>
              </div>
            </div>
          </div>

          {stats.collections.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] text-slate-400">集合列表</p>
              {stats.collections.map((c) => (
                <div key={c.name} className="flex items-center justify-between rounded bg-slate-800/60 px-2 py-1">
                  <span className="text-[10px] text-slate-300">{c.name}</span>
                  <span className="text-[9px] text-slate-500">{c.count} 筆</span>
                </div>
              ))}
            </div>
          )}

          {stats.collections.length === 0 && (
            <p className="text-center text-[10px] text-slate-600">知識庫目前為空，可透過 API 匯入文件</p>
          )}
        </div>
      )}

      {activeView === 'stats' && !stats && !loading && (
        <p className="text-[10px] text-slate-600">載入統計中...</p>
      )}
    </div>
  )
}
