/**
 * ReportManagementPanel — 維運報告管理與即時生成控制面板。
 */

import { useState, useEffect } from 'react'
import { useTheme } from '../themes'
import { API_BASE } from '../config/api'
import { ReportPreview } from './ReportPreview'

interface ReportItem {
  id: string
  title: string
  created_at: string
}

export default function ReportManagementPanel() {
  const { theme } = useTheme()
  const [reports, setReports] = useState<ReportItem[]>([])
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null)
  const [selectedReportTitle, setSelectedReportTitle] = useState<string>('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const fetchReports = async () => {
    try {
      const res = await fetch(`${API_BASE}/reports`)
      if (res.ok) {
        const data = await res.json()
        // 依照建立時間倒序排序
        setReports(data.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()))
      }
    } catch (e) {
      console.error('無法載入維運報告列表:', e)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [])

  const handleGenerate = async (type: 'weekly' | 'monthly') => {
    setIsGenerating(true)
    setMsg(null)
    try {
      const res = await fetch(`${API_BASE}/reports/generate?report_type=${type}&turbine_id=all`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        setMsg(`🎉 ${data.detail} (ID: ${data.report.id})`)
        await fetchReports()
      } else {
        setMsg('❌ 生成報告失敗，請檢查後端日誌')
      }
    } catch (e) {
      setMsg(`❌ 連線 API 失敗: ${e}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const formatTime = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleString('zh-TW', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div className="space-y-4">
      {/* 標題與手動觸發按鈕 */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-sm font-semibold" style={{ color: theme.global.textPrimary }}>
            📋 正式維運報告與 PDF 列印
          </h3>
          <p className="text-[9px]" style={{ color: theme.global.textMuted }}>
            彙整風機 SCADA 發電效率、警報發生率與工單 SLA 簽備率，生成正式 HTML 週報與月報，並提供 PDF 列印
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleGenerate('weekly')}
            disabled={isGenerating}
            className="rounded border px-3 py-1.5 text-[10px] font-semibold transition-all hover:brightness-110 disabled:opacity-40"
            style={{ borderColor: theme.global.border, color: theme.global.textPrimary }}
          >
            {isGenerating ? '生成中...' : '即時生成週報 📊'}
          </button>
          <button
            onClick={() => handleGenerate('monthly')}
            disabled={isGenerating}
            className="rounded px-3 py-1.5 text-[10px] font-semibold text-white transition-all hover:brightness-110 disabled:opacity-40"
            style={{ backgroundColor: theme.global.accent }}
          >
            {isGenerating ? '生成中...' : '即時生成月報 🏆'}
          </button>
        </div>
      </div>

      {msg && (
        <div className="rounded p-2 text-[10px]" 
          style={{ backgroundColor: theme.global.accent + '15', color: theme.global.textPrimary }}>
          📢 {msg}
        </div>
      )}

      {/* 歷史報告列表 Table */}
      <div className="rounded-lg border overflow-hidden" style={{ borderColor: theme.global.border + '40' }}>
        <table className="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr style={{ backgroundColor: theme.global.panelBg + '80', color: theme.global.textSecondary }}>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>報告標題</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>報告 ID</th>
              <th className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>生成時間</th>
              <th className="p-2 border-b text-center" style={{ borderColor: theme.global.border + '40' }}>操作選項</th>
            </tr>
          </thead>
          <tbody>
            {reports.map(rep => (
              <tr key={rep.id} style={{ color: theme.global.textPrimary }}>
                <td className="p-2 border-b font-medium" style={{ borderColor: theme.global.border + '40' }}>
                  📄 {rep.title}
                </td>
                <td className="p-2 border-b font-mono" style={{ borderColor: theme.global.border + '40' }}>
                  {rep.id}
                </td>
                <td className="p-2 border-b" style={{ borderColor: theme.global.border + '40' }}>
                  {formatTime(rep.created_at)}
                </td>
                <td className="p-2 border-b text-center space-x-1.5" style={{ borderColor: theme.global.border + '40' }}>
                  <button
                    onClick={() => {
                      setSelectedReportId(rep.id)
                      setSelectedReportTitle(rep.title)
                    }}
                    className="rounded px-2 py-1 text-[9px] font-semibold transition-colors hover:brightness-105"
                    style={{ backgroundColor: theme.global.accent + '15', color: theme.global.accent }}
                  >
                    預覽與列印 PDF 🖨️
                  </button>
                  <a
                    href={`${API_BASE}/reports/${rep.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-block rounded border px-2 py-1 text-[9px] font-semibold transition-colors hover:brightness-105"
                    style={{ borderColor: theme.global.border, color: theme.global.textSecondary }}
                  >
                    另存 HTML 📥
                  </a>
                </td>
              </tr>
            ))}
            {reports.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center text-muted" style={{ color: theme.global.textMuted }}>
                  目前尚無任何生成的維運報告，請點擊右上角按鈕即時生成。
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 彈出式 Modal 預覽列印 */}
      {selectedReportId && (
        <ReportPreview
          reportId={selectedReportId}
          title={selectedReportTitle}
          theme={theme}
          onClose={() => setSelectedReportId(null)}
        />
      )}
    </div>
  )
}
