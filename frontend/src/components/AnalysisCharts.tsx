/**
 * AnalysisCharts — 分析結果圖表的共用元件。
 *
 * 從 MissionView.tsx 提取出來，供 MissionPanel 與 TaskHistoryList 共用。
 */

import React from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, CartesianGrid,
  LineChart, Line, Legend,
} from 'recharts'
import type { WindAITheme } from '../themes'
import type { AnalysisResultPayload } from '../types/agent'

export function tooltipStyle(theme: WindAITheme) {
  return {
    contentStyle: {
      backgroundColor: theme.global.panelBg,
      border: `1px solid ${theme.global.border}`,
      borderRadius: 8,
      fontSize: 11,
      color: theme.global.textPrimary,
    },
  }
}

export function ChartPanel({ title, theme, children }: {
  title: string
  theme: WindAITheme
  children: React.ReactNode
}) {
  return (
    <div
      className="rounded-xl border p-4"
      style={{ backgroundColor: theme.global.panelBg, borderColor: theme.global.border }}
    >
      <h3 className="text-xs font-semibold mb-3" style={{ color: theme.global.textSecondary }}>
        {title}
      </h3>
      {children}
    </div>
  )
}

/** 根據 chart_type 渲染對應的圖表 */
export function AnalysisChart({ result, theme, height = 200 }: {
  result: AnalysisResultPayload
  theme: WindAITheme
  height?: number
}) {
  const { chart_type, title, data, metadata } = result

  if (chart_type === 'power_curve') {
    // 功率曲線專用：雙散佈圖（實際功率 + NBM 預測）
    const xKey = 'wind_speed'
    const xLabel = (metadata?.x_label as string) || '風速 (m/s)'
    const yLabel = (metadata?.y_label as string) || '功率 (kW)'
    const actualData = data.filter((d: any) => d.actual_power != null).map((d: any) => ({ [xKey]: d[xKey], y: d.actual_power }))
    const predictedData = data.filter((d: any) => d.predicted_power != null).map((d: any) => ({ [xKey]: d[xKey], y: d.predicted_power }))

    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={height + 40}>
          <ScatterChart margin={{ top: 8, right: 16, bottom: 20, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey={xKey} name={xLabel} tick={{ fontSize: 10, fill: theme.global.textMuted }} label={{ value: xLabel, position: 'bottom', fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis dataKey="y" name={yLabel} tick={{ fontSize: 10, fill: theme.global.textMuted }} label={{ value: yLabel, angle: -90, position: 'insideLeft', fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            <Scatter name="實際功率" data={actualData} fill={theme.global.accent} opacity={0.4} />
            {predictedData.length > 0 && (
              <Scatter name="NBM 預測" data={predictedData} fill={theme.statuses.error.dot} opacity={0.8} shape="diamond" />
            )}
          </ScatterChart>
        </ResponsiveContainer>
        {metadata && (
          <div className="flex flex-wrap gap-3 mt-2 text-[10px]" style={{ color: theme.global.textMuted }}>
            {Object.entries(metadata).filter(([k]) => !k.endsWith('_label') && k !== 'series').map(([k, v]) => (
              <span key={k}>{k}: <b style={{ color: theme.global.accent }}>{typeof v === 'number' ? (v < 1 ? v.toFixed(4) : v.toLocaleString()) : v}</b></span>
            ))}
          </div>
        )}
      </ChartPanel>
    )
  }

  if (chart_type === 'scatter') {
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={height}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="x" name={metadata?.x_label as string || 'X'} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis dataKey="y" name={metadata?.y_label as string || 'Y'} tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            <Scatter data={data} fill={theme.global.accent} />
          </ScatterChart>
        </ResponsiveContainer>
        {metadata && (
          <div className="flex gap-3 mt-2 text-[10px]" style={{ color: theme.global.textMuted }}>
            {Object.entries(metadata).filter(([k]) => !k.endsWith('_label')).map(([k, v]) => (
              <span key={k}>{k}: <b style={{ color: theme.global.accent }}>{typeof v === 'number' ? v.toFixed(4) : v}</b></span>
            ))}
          </div>
        )}
      </ChartPanel>
    )
  }

  if (chart_type === 'line' || chart_type === 'trend') {
    const keys = data.length > 0 ? Object.keys(data[0]).filter(k => k !== 'x' && k !== 'name') : []
    const colors = [theme.global.accent, theme.statuses.working.dot, theme.statuses.waiting.dot, theme.statuses.error.dot]
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="x" tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            <Legend wrapperStyle={{ fontSize: 10 }} />
            {keys.map((key, i) => (
              <Line key={key} type="monotone" dataKey={key} stroke={colors[i % colors.length]} dot={false} strokeWidth={2} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartPanel>
    )
  }

  if (chart_type === 'bar' || chart_type === 'histogram') {
    const keys = data.length > 0 ? Object.keys(data[0]).filter(k => k !== 'name' && k !== 'x') : []
    return (
      <ChartPanel title={title} theme={theme}>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.global.border} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <YAxis tick={{ fontSize: 10, fill: theme.global.textMuted }} />
            <Tooltip {...tooltipStyle(theme)} />
            {keys.map((key, i) => (
              <Bar key={key} dataKey={key} fill={i === 0 ? theme.global.accent : theme.statuses.working.dot} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    )
  }

  if (chart_type === 'report_link') {
    const downloadUrl = metadata?.download_url as string
    const apiBase = ''  // Vite proxy 模式，使用相對路徑
    return (
      <ChartPanel title={title} theme={theme}>
        <div className="flex flex-col items-center gap-3 py-4">
          <div className="text-[11px]" style={{ color: theme.global.textMuted }}>
            {metadata?.section_count ?? 0} 個章節 · {metadata?.warning_count ?? 0} 個警告
          </div>
          <a
            href={`${apiBase}${downloadUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg text-xs font-semibold transition-all hover:opacity-80"
            style={{
              backgroundColor: theme.global.accent,
              color: '#fff',
            }}
          >
            下載報告 (.md)
          </a>
          <div className="text-[9px]" style={{ color: theme.global.textMuted }}>
            {metadata?.generated_at ? `生成時間：${new Date(metadata.generated_at as string).toLocaleString('zh-TW')}` : ''}
          </div>
        </div>
      </ChartPanel>
    )
  }

  // 預設：顯示 metadata 為數據卡片
  return (
    <ChartPanel title={title} theme={theme}>
      {metadata && (
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(metadata).map(([k, v]) => (
            <div key={k} className="text-center py-2">
              <div className="text-[10px]" style={{ color: theme.global.textMuted }}>{k}</div>
              <div className="text-lg font-bold" style={{ color: theme.global.accent }}>
                {typeof v === 'number' ? v.toFixed(4) : v}
              </div>
            </div>
          ))}
        </div>
      )}
    </ChartPanel>
  )
}
