import { useState, useCallback } from 'react'
import { Search, BookOpen, Database, FolderInput, Loader2, MessageSquare, Sparkles, Trash2, FileText } from 'lucide-react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'

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

interface IngestResult {
  ingested: number
  total: number
  skipped: number
  chunks_added: number
  errors: string[]
  collection: string
  total_in_collection: number
}

interface AskResult {
  answer: string
  sources: { doc_id: string; source: string; relevance: number; content_preview: string }[]
  query: string
}

interface SourceItem {
  source: string
  chunks: number
  file_type: string
  file_path: string
}

type ViewType = 'ask' | 'search' | 'ingest' | 'manage'

export default function KnowledgeBasePanel() {
  const { theme } = useTheme()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [stats, setStats] = useState<KBStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<ViewType>('ask')

  // 問答 tab 狀態
  const [askResult, setAskResult] = useState<AskResult | null>(null)

  // 嵌入 tab 狀態
  const [folderPath, setFolderPath] = useState('')
  const [ingestResult, setIngestResult] = useState<IngestResult | null>(null)

  // 管理 tab 狀態
  const [sources, setSources] = useState<SourceItem[]>([])
  const [deleting, setDeleting] = useState<string | null>(null)

  // RAG 問答
  const handleAsk = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setAskResult(null)
    try {
      const res = await fetch(
        `${API_BASE}/knowledge-base/ask?query=${encodeURIComponent(query)}&n_results=5`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.status === 'error') setError(data.detail || '問答失敗')
      else setAskResult({ answer: data.answer, sources: data.sources, query: data.query })
    } catch { setError('無法連線至後端') }
    finally { setLoading(false) }
  }, [query])

  // 純檢索
  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/knowledge-base/search?query=${encodeURIComponent(query)}&n_results=10`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.status === 'error') setError(data.detail || '搜尋失敗')
      else setResults(data.results || [])
    } catch { setError('無法連線至後端') }
    finally { setLoading(false) }
  }, [query])

  // 載入管理資訊（sources + stats）
  const loadManage = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [srcRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/knowledge-base/sources`),
        fetch(`${API_BASE}/knowledge-base/stats`),
      ])
      const srcData = await srcRes.json()
      const statsData = await statsRes.json()
      if (srcData.status === 'success') setSources(srcData.sources || [])
      if (statsData.status === 'success') setStats(statsData)
    } catch { setError('無法連線至後端') }
    finally { setLoading(false) }
  }, [])

  // 刪除來源
  const handleDeleteSource = useCallback(async (source: string) => {
    if (!confirm(`確定要刪除「${source}」的所有 chunks 嗎？此操作無法復原。`)) return
    setDeleting(source)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/knowledge-base/source?source=${encodeURIComponent(source)}`,
        { method: 'DELETE' }
      )
      const data = await res.json()
      if (data.status === 'error') {
        setError(data.detail || '刪除失敗')
      } else {
        // 重新載入列表
        await loadManage()
      }
    } catch { setError('無法連線至後端') }
    finally { setDeleting(null) }
  }, [loadManage])

  const handleIngest = useCallback(async () => {
    if (!folderPath.trim()) return
    setLoading(true)
    setError(null)
    setIngestResult(null)
    try {
      const res = await fetch(
        `${API_BASE}/knowledge-base/ingest-folder?folder_path=${encodeURIComponent(folderPath)}`,
        { method: 'POST' }
      )
      const data = await res.json()
      if (data.status === 'error') setError(data.detail || '嵌入失敗')
      else setIngestResult(data)
    } catch { setError('無法連線至後端') }
    finally { setLoading(false) }
  }, [folderPath])

  const relevanceColor = (r: number) => {
    if (r >= 0.8) return theme.statuses.completed.dot
    if (r >= 0.5) return theme.statuses.waiting.dot
    return theme.global.textMuted
  }

  const tabStyle = (view: ViewType) => ({
    backgroundColor: activeView === view ? theme.global.border : 'transparent',
    color: activeView === view ? theme.global.textPrimary : theme.global.textMuted,
  })

  return (
    <div className="flex h-full flex-col gap-2 overflow-y-auto p-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-xs font-bold" style={{ color: theme.global.textSecondary }}>
          <BookOpen size={12} />
          RAG 知識庫
        </h3>
        <div className="flex gap-1">
          {(['ask', 'search', 'ingest', 'manage'] as ViewType[]).map((v) => (
            <button
              key={v}
              onClick={() => {
                setActiveView(v)
                setError(null)
                if (v === 'manage') loadManage()
              }}
              className="rounded px-2 py-0.5 text-[10px]"
              style={tabStyle(v)}
            >
              {{ ask: '問答', search: '搜尋', ingest: '嵌入', manage: '管理' }[v]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded px-2 py-1 text-[10px]" style={{ backgroundColor: theme.statuses.error.bg, color: theme.statuses.error.dot }}>
          {error}
        </div>
      )}

      {/* ── Ask view ── */}
      {activeView === 'ask' && (
        <>
          <div className="flex gap-1.5">
            <div className="relative flex-1">
              <MessageSquare size={12} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: theme.global.textMuted }} />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
                placeholder="輸入問題（如：Z72 風機的額定功率是多少？）"
                className="w-full rounded py-1.5 pl-7 pr-2 text-[10px] outline-none ring-1 focus:ring-2"
                style={{ backgroundColor: theme.global.panelBg, color: theme.global.textPrimary, '--tw-ring-color': theme.global.border } as React.CSSProperties}
              />
            </div>
            <button
              onClick={handleAsk}
              disabled={loading || !query.trim()}
              className="flex items-center gap-1 rounded px-2.5 text-[10px] font-medium text-white transition disabled:opacity-50"
              style={{ backgroundColor: theme.tiers['ai-ml'].primary }}
            >
              {loading ? <Loader2 size={10} className="animate-spin" /> : <><Sparkles size={10} /> 問答</>}
            </button>
          </div>

          {loading && (
            <div className="flex items-center gap-2 py-4 justify-center">
              <Loader2 size={14} className="animate-spin" style={{ color: theme.global.accent }} />
              <span className="text-[10px]" style={{ color: theme.global.textMuted }}>正在搜尋知識庫並整理回答...</span>
            </div>
          )}

          {askResult && (
            <div className="space-y-2">
              <div className="rounded p-3" style={{ backgroundColor: theme.tiers['ai-ml'].primary + '15', borderLeft: `3px solid ${theme.tiers['ai-ml'].primary}` }}>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <Sparkles size={10} style={{ color: theme.tiers['ai-ml'].primary }} />
                  <span className="text-[10px] font-bold" style={{ color: theme.tiers['ai-ml'].primary }}>AI 回答</span>
                </div>
                <div className="text-[11px] leading-relaxed whitespace-pre-wrap" style={{ color: theme.global.textPrimary }}>
                  {askResult.answer}
                </div>
              </div>
              {askResult.sources.length > 0 && (
                <div className="space-y-1">
                  <p className="text-[9px] font-medium" style={{ color: theme.global.textMuted }}>
                    參考來源（{askResult.sources.length} 份文件）
                  </p>
                  {askResult.sources.map((s, i) => (
                    <div key={s.doc_id} className="flex items-center justify-between rounded px-2 py-1" style={{ backgroundColor: theme.global.panelBg + '99' }}>
                      <span className="text-[9px]" style={{ color: theme.global.textSecondary }}>[{i + 1}] {s.source}</span>
                      <span className="text-[9px]" style={{ color: relevanceColor(s.relevance) }}>{(s.relevance * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {!askResult && !loading && (
            <p className="text-[10px]" style={{ color: theme.global.textMuted }}>
              輸入問題，AI 會從知識庫中檢索相關文件並整理回答。
            </p>
          )}
        </>
      )}

      {/* ── Search view ── */}
      {activeView === 'search' && (
        <>
          <div className="flex gap-1.5">
            <div className="relative flex-1">
              <Search size={12} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: theme.global.textMuted }} />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="輸入搜尋查詢"
                className="w-full rounded py-1.5 pl-7 pr-2 text-[10px] outline-none ring-1 focus:ring-2"
                style={{ backgroundColor: theme.global.panelBg, color: theme.global.textPrimary, '--tw-ring-color': theme.global.border } as React.CSSProperties}
              />
            </div>
            <button onClick={handleSearch} disabled={loading || !query.trim()} className="rounded px-2.5 text-[10px] font-medium text-white transition disabled:opacity-50" style={{ backgroundColor: theme.global.accent }}>
              {loading ? '...' : '搜尋'}
            </button>
          </div>
          {results.length > 0 && (
            <div className="space-y-2">
              <p className="text-[9px]" style={{ color: theme.global.textMuted }}>找到 {results.length} 筆結果</p>
              {results.map((r) => (
                <div key={r.doc_id} className="rounded p-2" style={{ backgroundColor: theme.global.panelBg + 'cc' }}>
                  <div className="flex items-center justify-between">
                    <span className="text-[9px]" style={{ color: theme.global.textMuted }}>{r.doc_id.slice(0, 8)}...</span>
                    <span className="text-[9px] font-medium" style={{ color: relevanceColor(r.relevance) }}>相關度 {(r.relevance * 100).toFixed(0)}%</span>
                  </div>
                  <p className="mt-1 text-[10px] leading-relaxed" style={{ color: theme.global.textSecondary }}>{r.content}</p>
                  {r.metadata.source && <p className="mt-1 text-[9px]" style={{ color: theme.global.textMuted }}>來源：{String(r.metadata.source)}</p>}
                </div>
              ))}
            </div>
          )}
          {results.length === 0 && !loading && query && (
            <p className="text-center text-[10px]" style={{ color: theme.global.textMuted }}>無搜尋結果</p>
          )}
          {!query && results.length === 0 && (
            <p className="text-[10px]" style={{ color: theme.global.textMuted }}>純向量檢索，顯示原始文件片段（不經 LLM）。</p>
          )}
        </>
      )}

      {/* ── Ingest view ── */}
      {activeView === 'ingest' && (
        <>
          <div className="flex gap-1.5">
            <div className="relative flex-1">
              <FolderInput size={12} className="absolute left-2 top-1/2 -translate-y-1/2" style={{ color: theme.global.textMuted }} />
              <input
                type="text"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleIngest()}
                placeholder="輸入檔案或資料夾路徑（支援 PDF/TXT/MD）"
                className="w-full rounded py-1.5 pl-7 pr-2 text-[10px] outline-none ring-1 focus:ring-2"
                style={{ backgroundColor: theme.global.panelBg, color: theme.global.textPrimary, '--tw-ring-color': theme.global.border } as React.CSSProperties}
              />
            </div>
            <button onClick={handleIngest} disabled={loading || !folderPath.trim()} className="rounded px-2.5 text-[10px] font-medium text-white transition disabled:opacity-50" style={{ backgroundColor: theme.global.accent }}>
              {loading ? <Loader2 size={10} className="animate-spin" /> : '嵌入'}
            </button>
          </div>
          {ingestResult && (
            <div className="space-y-1.5 rounded p-2" style={{ backgroundColor: theme.global.panelBg + 'cc' }}>
              <span className="text-[10px] font-medium" style={{ color: theme.statuses.completed.dot }}>嵌入完成</span>
              <div className="grid grid-cols-2 gap-1.5 text-[9px]">
                <div><span style={{ color: theme.global.textMuted }}>已嵌入：</span><span style={{ color: theme.global.textPrimary }}>{ingestResult.ingested}/{ingestResult.total} 份</span></div>
                <div><span style={{ color: theme.global.textMuted }}>Chunks：</span><span style={{ color: theme.global.textPrimary }}>{ingestResult.chunks_added}</span></div>
                <div><span style={{ color: theme.global.textMuted }}>知識庫總量：</span><span style={{ color: theme.global.textPrimary }}>{ingestResult.total_in_collection}</span></div>
                {ingestResult.errors.length > 0 && <div><span style={{ color: theme.statuses.error.dot }}>失敗 {ingestResult.errors.length} 份</span></div>}
              </div>
            </div>
          )}
          {!ingestResult && !loading && (
            <p className="text-[10px]" style={{ color: theme.global.textMuted }}>支援單一檔案或資料夾路徑（PDF/TXT/MD），資料夾會遞迴掃描。</p>
          )}
        </>
      )}

      {/* ── Manage view ── */}
      {activeView === 'manage' && (
        <div className="space-y-2">
          {/* 統計摘要 */}
          {stats && (
            <div className="flex gap-3">
              <div className="flex items-center gap-1.5 rounded px-2 py-1.5" style={{ backgroundColor: theme.global.panelBg + 'cc' }}>
                <Database size={12} style={{ color: theme.global.accent }} />
                <div>
                  <p className="text-[9px]" style={{ color: theme.global.textMuted }}>集合數</p>
                  <p className="text-sm font-bold" style={{ color: theme.global.textPrimary }}>{stats.total_collections}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 rounded px-2 py-1.5" style={{ backgroundColor: theme.global.panelBg + 'cc' }}>
                <FileText size={12} style={{ color: theme.tiers['ai-ml'].primary }} />
                <div>
                  <p className="text-[9px]" style={{ color: theme.global.textMuted }}>總 Chunks</p>
                  <p className="text-sm font-bold" style={{ color: theme.global.textPrimary }}>{stats.total_documents}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 rounded px-2 py-1.5" style={{ backgroundColor: theme.global.panelBg + 'cc' }}>
                <BookOpen size={12} style={{ color: theme.tiers.research.primary }} />
                <div>
                  <p className="text-[9px]" style={{ color: theme.global.textMuted }}>來源檔案</p>
                  <p className="text-sm font-bold" style={{ color: theme.global.textPrimary }}>{sources.length}</p>
                </div>
              </div>
            </div>
          )}

          {/* 來源檔案列表 */}
          {sources.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] font-medium" style={{ color: theme.global.textSecondary }}>來源檔案</p>
              {sources.map((s) => (
                <div
                  key={s.source}
                  className="flex items-center justify-between rounded px-2 py-1.5 group"
                  style={{ backgroundColor: theme.global.panelBg + '99' }}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] truncate" style={{ color: theme.global.textSecondary }} title={s.file_path || s.source}>
                      {s.source}
                    </p>
                    <p className="text-[9px]" style={{ color: theme.global.textMuted }}>
                      {s.file_type.toUpperCase()} · {s.chunks} chunks
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteSource(s.source)}
                    disabled={deleting === s.source}
                    className="ml-2 flex-shrink-0 rounded p-1 opacity-60 hover:opacity-100 transition disabled:opacity-30"
                    style={{ color: theme.statuses.error.dot }}
                    title={`刪除 ${s.source}`}
                  >
                    {deleting === s.source ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                  </button>
                </div>
              ))}
            </div>
          )}

          {sources.length === 0 && !loading && (
            <p className="text-center text-[10px]" style={{ color: theme.global.textMuted }}>知識庫目前為空</p>
          )}

          {loading && (
            <div className="flex items-center gap-2 py-2 justify-center">
              <Loader2 size={12} className="animate-spin" style={{ color: theme.global.accent }} />
              <span className="text-[10px]" style={{ color: theme.global.textMuted }}>載入中...</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
