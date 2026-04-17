/**
 * ReportPreview — 診斷報告內嵌預覽 Modal。
 *
 * 透過 /api/reports/{id} 取得 Markdown 內容，在 Modal 中以基本格式渲染。
 * 支援關閉按鈕、背景點擊關閉、ESC 鍵關閉。
 */

import React, { useEffect, useState } from 'react'
import type { WindAITheme } from '../themes'

type Props = {
  reportId: string
  title?: string
  theme: WindAITheme
  onClose: () => void
}

/** 簡易 Markdown → 可讀 HTML 轉換（處理常見語法）。 */
function renderMarkdown(md: string): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = esc(md).split('\n')
  const html: string[] = []
  let inTable = false
  for (const raw of lines) {
    const line = raw
    if (/^### /.test(line)) html.push(`<h3>${line.slice(4)}</h3>`)
    else if (/^## /.test(line)) html.push(`<h2>${line.slice(3)}</h2>`)
    else if (/^# /.test(line)) html.push(`<h1>${line.slice(2)}</h1>`)
    else if (/^\|.+\|$/.test(line)) {
      if (!inTable) {
        html.push('<table class="wl-table">')
        inTable = true
      }
      const cells = line.split('|').slice(1, -1).map((c) => c.trim())
      if (cells.every((c) => /^-+$/.test(c))) continue
      const row = cells.map((c) => `<td>${c}</td>`).join('')
      html.push(`<tr>${row}</tr>`)
    } else {
      if (inTable) {
        html.push('</table>')
        inTable = false
      }
      const bolded = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      if (/^- /.test(bolded)) html.push(`<li>${bolded.slice(2)}</li>`)
      else if (line.trim() === '') html.push('<br/>')
      else if (line.trim() === '---') html.push('<hr/>')
      else html.push(`<p>${bolded}</p>`)
    }
  }
  if (inTable) html.push('</table>')
  return html.join('\n')
}

export function ReportPreview({ reportId, title, theme, onClose }: Props) {
  const [markdown, setMarkdown] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    fetch(`/api/reports/${reportId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((d) => {
        if (alive) setMarkdown(d.markdown || '')
      })
      .catch((e) => {
        if (alive) setError(String(e))
      })
    return () => {
      alive = false
    }
  }, [reportId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl max-h-[85vh] overflow-auto rounded-lg shadow-2xl"
        style={{
          backgroundColor: theme.global.panelBg,
          border: `1px solid ${theme.global.border}`,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="flex items-center justify-between px-5 py-3 sticky top-0 border-b"
          style={{
            backgroundColor: theme.global.panelBg,
            borderColor: theme.global.border,
          }}
        >
          <h2 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
            📄 {title || '診斷報告預覽'}
          </h2>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded hover:opacity-80 text-xs"
            style={{ color: theme.global.textSecondary }}
          >
            ✕ 關閉 (Esc)
          </button>
        </div>
        <div
          className="px-6 py-4 text-sm wl-report-body"
          style={{ color: theme.global.textPrimary }}
        >
          {error && (
            <div className="text-xs" style={{ color: theme.statuses.error.dot }}>
              載入失敗：{error}
            </div>
          )}
          {!error && markdown === null && (
            <div className="text-xs" style={{ color: theme.global.textMuted }}>
              載入中...
            </div>
          )}
          {markdown !== null && (
            <div
              className="prose-compact"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(markdown) }}
            />
          )}
        </div>
      </div>
    </div>
  )
}
