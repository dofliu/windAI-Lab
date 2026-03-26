/**
 * WindAI Lab 主題系統 — 型別定義與預設主題。
 *
 * 所有視覺資產（配色、代理頭像色系、狀態顏色、房間顏色、全域色板）
 * 集中在此處定義，透過 CSS custom properties 注入到整個應用程式。
 *
 * 更換主題只需提供一個新的 WindAITheme 物件。
 */

// ── 型別定義 ──────────────────────────────────────────────────

/** 代理層級（團隊）配色 */
export interface TierColors {
  /** Tailwind 顏色名（如 'amber', 'emerald'） */
  name: string
  /** 主色 hex */
  primary: string
  /** 背景色 hex（深色，用於卡片） */
  bg: string
  /** 淺色背景 hex（用於 hover） */
  bgLight: string
}

/** 代理狀態配色 */
export interface StatusColors {
  dot: string
  bg: string
  text: string
}

/** 房間配色 */
export interface RoomColors {
  border: string
  floor: string
  label: string
}

/** 全域色板 */
export interface GlobalPalette {
  /** 主背景色 */
  pageBg: string
  /** 面板/卡片背景色 */
  panelBg: string
  /** 標題列背景色 */
  headerBg: string
  /** 主要文字色 */
  textPrimary: string
  /** 次要文字色 */
  textSecondary: string
  /** 靜音文字色 */
  textMuted: string
  /** 邊框色 */
  border: string
  /** 強調色 */
  accent: string
  /** 強調色（hover） */
  accentHover: string
}

/** 完整主題定義 */
export interface WindAITheme {
  /** 主題 ID */
  id: string
  /** 主題顯示名稱 */
  name: string
  /** 是否為深色主題 */
  isDark: boolean

  /** 全域色板 */
  global: GlobalPalette

  /** 代理層級配色 */
  tiers: Record<string, TierColors>

  /** 代理狀態配色 */
  statuses: Record<string, StatusColors>

  /** 房間配色 */
  rooms: Record<string, RoomColors>

  /** 像素角色襯衫顏色（覆蓋 tier primary） */
  pixelShirtColors?: Record<string, string>
}

// ── 預設主題：深色科技風 ──────────────────────────────────────

export const defaultTheme: WindAITheme = {
  id: 'dark-default',
  name: '深色科技',
  isDark: true,

  global: {
    pageBg: '#0f172a',       // slate-900
    panelBg: '#1e293b',      // slate-800
    headerBg: '#1e293b',     // slate-800
    textPrimary: '#f1f5f9',  // slate-100
    textSecondary: '#94a3b8', // slate-400
    textMuted: '#475569',    // slate-600
    border: '#334155',       // slate-700
    accent: '#3b82f6',       // blue-500
    accentHover: '#2563eb',  // blue-600
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#d97706', bg: '#78350f', bgLight: '#92400e' },
    data:        { name: 'emerald', primary: '#059669', bg: '#064e3b', bgLight: '#065f46' },
    'ai-ml':     { name: 'violet',  primary: '#7c3aed', bg: '#4c1d95', bgLight: '#5b21b6' },
    domain:      { name: 'pink',    primary: '#db2777', bg: '#831843', bgLight: '#9d174d' },
    engineering: { name: 'orange',  primary: '#ea580c', bg: '#7c2d12', bgLight: '#9a3412' },
    research:    { name: 'cyan',    primary: '#0891b2', bg: '#164e63', bgLight: '#155e75' },
  },

  statuses: {
    idle:      { dot: '#94a3b8', bg: '#334155',   text: '#94a3b8' },
    working:   { dot: '#34d399', bg: '#064e3b',   text: '#34d399' },
    waiting:   { dot: '#fbbf24', bg: '#78350f',   text: '#fbbf24' },
    completed: { dot: '#60a5fa', bg: '#1e3a5f',   text: '#60a5fa' },
    error:     { dot: '#ef4444', bg: '#7f1d1d',   text: '#ef4444' },
    offline:   { dot: '#6b7280', bg: '#1f2937',   text: '#6b7280' },
  },

  rooms: {
    leadership:  { border: 'rgba(245,158,11,0.4)', floor: 'rgba(245,158,11,0.06)', label: '#f59e0b' },
    data:        { border: 'rgba(16,185,129,0.4)', floor: 'rgba(16,185,129,0.06)', label: '#10b981' },
    'ai-ml':     { border: 'rgba(139,92,246,0.4)', floor: 'rgba(139,92,246,0.06)', label: '#8b5cf6' },
    domain:      { border: 'rgba(236,72,153,0.4)', floor: 'rgba(236,72,153,0.06)', label: '#ec4899' },
    engineering: { border: 'rgba(249,115,22,0.4)', floor: 'rgba(249,115,22,0.06)', label: '#f97316' },
    research:    { border: 'rgba(6,182,212,0.4)',  floor: 'rgba(6,182,212,0.06)',  label: '#06b6d4' },
    meeting:     { border: 'rgba(99,102,241,0.4)', floor: 'rgba(99,102,241,0.06)', label: '#6366f1' },
    'boss-room': { border: 'rgba(234,179,8,0.5)',  floor: 'rgba(234,179,8,0.08)',  label: '#eab308' },
    'tea-room':  { border: 'rgba(34,197,94,0.4)',  floor: 'rgba(34,197,94,0.06)',  label: '#22c55e' },
    'game-room': { border: 'rgba(244,63,94,0.4)',  floor: 'rgba(244,63,94,0.06)',  label: '#f43f5e' },
  },
}

// ── 主題工具函式 ──────────────────────────────────────────────

/** 將主題注入為 CSS custom properties */
export function applyThemeToRoot(theme: WindAITheme): void {
  const root = document.documentElement.style

  // 全域色板
  root.setProperty('--wai-page-bg', theme.global.pageBg)
  root.setProperty('--wai-panel-bg', theme.global.panelBg)
  root.setProperty('--wai-header-bg', theme.global.headerBg)
  root.setProperty('--wai-text-primary', theme.global.textPrimary)
  root.setProperty('--wai-text-secondary', theme.global.textSecondary)
  root.setProperty('--wai-text-muted', theme.global.textMuted)
  root.setProperty('--wai-border', theme.global.border)
  root.setProperty('--wai-accent', theme.global.accent)
  root.setProperty('--wai-accent-hover', theme.global.accentHover)

  // 層級色
  for (const [tier, colors] of Object.entries(theme.tiers)) {
    root.setProperty(`--wai-tier-${tier}`, colors.primary)
    root.setProperty(`--wai-tier-${tier}-bg`, colors.bg)
    root.setProperty(`--wai-tier-${tier}-bg-light`, colors.bgLight)
  }

  // 狀態色
  for (const [status, colors] of Object.entries(theme.statuses)) {
    root.setProperty(`--wai-status-${status}-dot`, colors.dot)
    root.setProperty(`--wai-status-${status}-bg`, colors.bg)
    root.setProperty(`--wai-status-${status}-text`, colors.text)
  }
}

/** 取得層級的 Tailwind 相容色名 */
export function getTierColor(theme: WindAITheme, tier: string): TierColors {
  return theme.tiers[tier] ?? theme.tiers['research']
}

/** 取得狀態的配色 */
export function getStatusColor(theme: WindAITheme, status: string): StatusColors {
  return theme.statuses[status] ?? theme.statuses['idle']
}

/** 取得房間的配色 */
export function getRoomColor(theme: WindAITheme, roomId: string): RoomColors {
  return theme.rooms[roomId] ?? theme.rooms['meeting']
}
