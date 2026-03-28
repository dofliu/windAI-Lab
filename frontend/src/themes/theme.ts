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

  /**
   * 視覺風格 ID — 對應 OfficeRenderer 的 id。
   * 決定辦公室用哪個 renderer 渲染（pixel / modern / minimal 等）。
   * 切換主題時會自動切換對應的辦公室風格。
   */
  visualStyle: string

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
  visualStyle: 'pixel',

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

// ── 深色森林 ────────────────────────────────────────────────

export const darkForest: WindAITheme = {
  id: 'dark-forest',
  name: '深色森林',
  isDark: true,
  visualStyle: 'pixel',

  global: {
    pageBg: '#0c1a14',
    panelBg: '#142a1e',
    headerBg: '#142a1e',
    textPrimary: '#e8f5e9',
    textSecondary: '#81c784',
    textMuted: '#4a6b52',
    border: '#2e5940',
    accent: '#4caf50',
    accentHover: '#388e3c',
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#e6a817', bg: '#5c3f0a', bgLight: '#7a5410' },
    data:        { name: 'emerald', primary: '#2dd4bf', bg: '#0d3b36', bgLight: '#115e56' },
    'ai-ml':     { name: 'lime',    primary: '#84cc16', bg: '#1a3a08', bgLight: '#2d5a10' },
    domain:      { name: 'rose',    primary: '#e879a0', bg: '#5c1a30', bgLight: '#7a2240' },
    engineering: { name: 'orange',  primary: '#fb923c', bg: '#5c2a0e', bgLight: '#7a3812' },
    research:    { name: 'teal',    primary: '#2dd4bf', bg: '#0d3b36', bgLight: '#115e56' },
  },

  statuses: {
    idle:      { dot: '#81c784', bg: '#1b3a20', text: '#81c784' },
    working:   { dot: '#66bb6a', bg: '#1b4a22', text: '#66bb6a' },
    waiting:   { dot: '#ffb74d', bg: '#5c3f0a', text: '#ffb74d' },
    completed: { dot: '#4fc3f7', bg: '#0e3b50', text: '#4fc3f7' },
    error:     { dot: '#ef5350', bg: '#5c1515', text: '#ef5350' },
    offline:   { dot: '#78909c', bg: '#1a2c20', text: '#78909c' },
  },

  rooms: {
    leadership:  { border: 'rgba(230,168,23,0.4)', floor: 'rgba(230,168,23,0.06)', label: '#e6a817' },
    data:        { border: 'rgba(45,212,191,0.4)', floor: 'rgba(45,212,191,0.06)', label: '#2dd4bf' },
    'ai-ml':     { border: 'rgba(132,204,22,0.4)', floor: 'rgba(132,204,22,0.06)', label: '#84cc16' },
    domain:      { border: 'rgba(232,121,160,0.4)', floor: 'rgba(232,121,160,0.06)', label: '#e879a0' },
    engineering: { border: 'rgba(251,146,60,0.4)', floor: 'rgba(251,146,60,0.06)', label: '#fb923c' },
    research:    { border: 'rgba(45,212,191,0.4)', floor: 'rgba(45,212,191,0.06)', label: '#2dd4bf' },
    meeting:     { border: 'rgba(76,175,80,0.5)',  floor: 'rgba(76,175,80,0.08)',  label: '#4caf50' },
    'boss-room': { border: 'rgba(230,168,23,0.5)', floor: 'rgba(230,168,23,0.08)', label: '#e6a817' },
    'tea-room':  { border: 'rgba(102,187,106,0.4)', floor: 'rgba(102,187,106,0.06)', label: '#66bb6a' },
    'game-room': { border: 'rgba(239,83,80,0.4)',  floor: 'rgba(239,83,80,0.06)',  label: '#ef5350' },
  },
}

// ── 深色海洋 ────────────────────────────────────────────────

export const darkOcean: WindAITheme = {
  id: 'dark-ocean',
  name: '深色海洋',
  isDark: true,
  visualStyle: 'pixel',

  global: {
    pageBg: '#0a1628',
    panelBg: '#0f2035',
    headerBg: '#0f2035',
    textPrimary: '#e0f2fe',
    textSecondary: '#7dd3fc',
    textMuted: '#3b6a8c',
    border: '#1e4976',
    accent: '#0ea5e9',
    accentHover: '#0284c7',
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#fbbf24', bg: '#5c3f0a', bgLight: '#7a5410' },
    data:        { name: 'sky',     primary: '#38bdf8', bg: '#0c3554', bgLight: '#0e4a70' },
    'ai-ml':     { name: 'indigo',  primary: '#818cf8', bg: '#252880', bgLight: '#3034a0' },
    domain:      { name: 'pink',    primary: '#f472b6', bg: '#5c1a42', bgLight: '#7a2258' },
    engineering: { name: 'orange',  primary: '#fb923c', bg: '#5c2a0e', bgLight: '#7a3812' },
    research:    { name: 'cyan',    primary: '#22d3ee', bg: '#0c4a5e', bgLight: '#0e5c74' },
  },

  statuses: {
    idle:      { dot: '#7dd3fc', bg: '#0c3554', text: '#7dd3fc' },
    working:   { dot: '#34d399', bg: '#064e3b', text: '#34d399' },
    waiting:   { dot: '#fcd34d', bg: '#5c3f0a', text: '#fcd34d' },
    completed: { dot: '#60a5fa', bg: '#1e3a8a', text: '#60a5fa' },
    error:     { dot: '#f87171', bg: '#7f1d1d', text: '#f87171' },
    offline:   { dot: '#6b7280', bg: '#0f2035', text: '#6b7280' },
  },

  rooms: {
    leadership:  { border: 'rgba(251,191,36,0.4)', floor: 'rgba(251,191,36,0.06)', label: '#fbbf24' },
    data:        { border: 'rgba(56,189,248,0.4)', floor: 'rgba(56,189,248,0.06)', label: '#38bdf8' },
    'ai-ml':     { border: 'rgba(129,140,248,0.4)', floor: 'rgba(129,140,248,0.06)', label: '#818cf8' },
    domain:      { border: 'rgba(244,114,182,0.4)', floor: 'rgba(244,114,182,0.06)', label: '#f472b6' },
    engineering: { border: 'rgba(251,146,60,0.4)', floor: 'rgba(251,146,60,0.06)', label: '#fb923c' },
    research:    { border: 'rgba(34,211,238,0.4)', floor: 'rgba(34,211,238,0.06)', label: '#22d3ee' },
    meeting:     { border: 'rgba(14,165,233,0.5)', floor: 'rgba(14,165,233,0.08)', label: '#0ea5e9' },
    'boss-room': { border: 'rgba(251,191,36,0.5)', floor: 'rgba(251,191,36,0.08)', label: '#fbbf24' },
    'tea-room':  { border: 'rgba(52,211,153,0.4)', floor: 'rgba(52,211,153,0.06)', label: '#34d399' },
    'game-room': { border: 'rgba(248,113,113,0.4)', floor: 'rgba(248,113,113,0.06)', label: '#f87171' },
  },
}

// ── 淺色簡約 ────────────────────────────────────────────────

export const lightClean: WindAITheme = {
  id: 'light-clean',
  name: '淺色簡約',
  isDark: false,
  visualStyle: 'pixel',

  global: {
    pageBg: '#f8fafc',
    panelBg: '#ffffff',
    headerBg: '#ffffff',
    textPrimary: '#1e293b',
    textSecondary: '#475569',
    textMuted: '#94a3b8',
    border: '#e2e8f0',
    accent: '#4f46e5',
    accentHover: '#4338ca',
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#d97706', bg: '#fef3c7', bgLight: '#fde68a' },
    data:        { name: 'emerald', primary: '#059669', bg: '#d1fae5', bgLight: '#a7f3d0' },
    'ai-ml':     { name: 'violet',  primary: '#7c3aed', bg: '#ede9fe', bgLight: '#ddd6fe' },
    domain:      { name: 'pink',    primary: '#db2777', bg: '#fce7f3', bgLight: '#fbcfe8' },
    engineering: { name: 'orange',  primary: '#ea580c', bg: '#fff7ed', bgLight: '#fed7aa' },
    research:    { name: 'cyan',    primary: '#0891b2', bg: '#cffafe', bgLight: '#a5f3fc' },
  },

  statuses: {
    idle:      { dot: '#94a3b8', bg: '#f1f5f9', text: '#64748b' },
    working:   { dot: '#059669', bg: '#d1fae5', text: '#059669' },
    waiting:   { dot: '#d97706', bg: '#fef3c7', text: '#d97706' },
    completed: { dot: '#2563eb', bg: '#dbeafe', text: '#2563eb' },
    error:     { dot: '#dc2626', bg: '#fee2e2', text: '#dc2626' },
    offline:   { dot: '#9ca3af', bg: '#f3f4f6', text: '#9ca3af' },
  },

  rooms: {
    leadership:  { border: 'rgba(217,119,6,0.3)',  floor: 'rgba(217,119,6,0.05)',  label: '#d97706' },
    data:        { border: 'rgba(5,150,105,0.3)',   floor: 'rgba(5,150,105,0.05)',  label: '#059669' },
    'ai-ml':     { border: 'rgba(124,58,237,0.3)',  floor: 'rgba(124,58,237,0.05)', label: '#7c3aed' },
    domain:      { border: 'rgba(219,39,119,0.3)',  floor: 'rgba(219,39,119,0.05)', label: '#db2777' },
    engineering: { border: 'rgba(234,88,12,0.3)',   floor: 'rgba(234,88,12,0.05)',  label: '#ea580c' },
    research:    { border: 'rgba(8,145,178,0.3)',   floor: 'rgba(8,145,178,0.05)',  label: '#0891b2' },
    meeting:     { border: 'rgba(79,70,229,0.3)',   floor: 'rgba(79,70,229,0.05)',  label: '#4f46e5' },
    'boss-room': { border: 'rgba(217,119,6,0.4)',   floor: 'rgba(217,119,6,0.06)',  label: '#d97706' },
    'tea-room':  { border: 'rgba(5,150,105,0.3)',   floor: 'rgba(5,150,105,0.05)',  label: '#059669' },
    'game-room': { border: 'rgba(220,38,38,0.3)',   floor: 'rgba(220,38,38,0.05)',  label: '#dc2626' },
  },
}

// ── 現代企業風（全新視覺風格：glassmorphism + 圓角卡片） ───

export const modernCorporate: WindAITheme = {
  id: 'modern-corporate',
  name: '現代企業',
  isDark: true,
  visualStyle: 'modern',

  global: {
    pageBg: '#09090b',        // zinc-950
    panelBg: '#18181b',       // zinc-900
    headerBg: '#18181b',
    textPrimary: '#fafafa',
    textSecondary: '#a1a1aa',
    textMuted: '#52525b',
    border: '#27272a',
    accent: '#a78bfa',        // violet-400
    accentHover: '#8b5cf6',
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#fbbf24', bg: '#1c1917', bgLight: '#292524' },
    data:        { name: 'emerald', primary: '#34d399', bg: '#0c1917', bgLight: '#132420' },
    'ai-ml':     { name: 'violet',  primary: '#a78bfa', bg: '#1a1625', bgLight: '#251e36' },
    domain:      { name: 'rose',    primary: '#fb7185', bg: '#1c1015', bgLight: '#2a1820' },
    engineering: { name: 'orange',  primary: '#fb923c', bg: '#1c1510', bgLight: '#2a2018' },
    research:    { name: 'sky',     primary: '#38bdf8', bg: '#0c1522', bgLight: '#122030' },
  },

  statuses: {
    idle:      { dot: '#71717a', bg: '#27272a', text: '#a1a1aa' },
    working:   { dot: '#34d399', bg: '#052e16', text: '#34d399' },
    waiting:   { dot: '#fbbf24', bg: '#422006', text: '#fbbf24' },
    completed: { dot: '#a78bfa', bg: '#2e1065', text: '#a78bfa' },
    error:     { dot: '#f87171', bg: '#450a0a', text: '#f87171' },
    offline:   { dot: '#52525b', bg: '#18181b', text: '#52525b' },
  },

  rooms: {
    leadership:  { border: 'rgba(251,191,36,0.25)', floor: 'rgba(251,191,36,0.04)', label: '#fbbf24' },
    data:        { border: 'rgba(52,211,153,0.25)', floor: 'rgba(52,211,153,0.04)', label: '#34d399' },
    'ai-ml':     { border: 'rgba(167,139,250,0.25)', floor: 'rgba(167,139,250,0.04)', label: '#a78bfa' },
    domain:      { border: 'rgba(251,113,133,0.25)', floor: 'rgba(251,113,133,0.04)', label: '#fb7185' },
    engineering: { border: 'rgba(251,146,60,0.25)',  floor: 'rgba(251,146,60,0.04)',  label: '#fb923c' },
    research:    { border: 'rgba(56,189,248,0.25)',  floor: 'rgba(56,189,248,0.04)',  label: '#38bdf8' },
    meeting:     { border: 'rgba(167,139,250,0.3)',  floor: 'rgba(167,139,250,0.05)', label: '#a78bfa' },
    'boss-room': { border: 'rgba(251,191,36,0.3)',   floor: 'rgba(251,191,36,0.05)',  label: '#fbbf24' },
    'tea-room':  { border: 'rgba(52,211,153,0.25)',  floor: 'rgba(52,211,153,0.04)',  label: '#34d399' },
    'game-room': { border: 'rgba(251,113,133,0.25)', floor: 'rgba(251,113,133,0.04)', label: '#fb7185' },
  },
}

// ── 極簡白板風（全新視覺風格：手繪線條 + 極簡佈局） ─────────

export const minimalWhiteboard: WindAITheme = {
  id: 'minimal-whiteboard',
  name: '極簡白板',
  isDark: false,
  visualStyle: 'minimal',

  global: {
    pageBg: '#fefefe',
    panelBg: '#ffffff',
    headerBg: '#fefefe',
    textPrimary: '#1a1a1a',
    textSecondary: '#666666',
    textMuted: '#aaaaaa',
    border: '#e0e0e0',
    accent: '#1a1a1a',
    accentHover: '#333333',
  },

  tiers: {
    leadership:  { name: 'amber',   primary: '#b45309', bg: '#fffbeb', bgLight: '#fef3c7' },
    data:        { name: 'emerald', primary: '#047857', bg: '#ecfdf5', bgLight: '#d1fae5' },
    'ai-ml':     { name: 'violet',  primary: '#6d28d9', bg: '#f5f3ff', bgLight: '#ede9fe' },
    domain:      { name: 'rose',    primary: '#be123c', bg: '#fff1f2', bgLight: '#ffe4e6' },
    engineering: { name: 'orange',  primary: '#c2410c', bg: '#fff7ed', bgLight: '#ffedd5' },
    research:    { name: 'sky',     primary: '#0369a1', bg: '#f0f9ff', bgLight: '#e0f2fe' },
  },

  statuses: {
    idle:      { dot: '#d4d4d4', bg: '#fafafa', text: '#a3a3a3' },
    working:   { dot: '#22c55e', bg: '#f0fdf4', text: '#15803d' },
    waiting:   { dot: '#eab308', bg: '#fefce8', text: '#a16207' },
    completed: { dot: '#6366f1', bg: '#eef2ff', text: '#4338ca' },
    error:     { dot: '#ef4444', bg: '#fef2f2', text: '#b91c1c' },
    offline:   { dot: '#d4d4d4', bg: '#fafafa', text: '#a3a3a3' },
  },

  rooms: {
    leadership:  { border: '#b45309', floor: 'rgba(180,83,9,0.03)',  label: '#b45309' },
    data:        { border: '#047857', floor: 'rgba(4,120,87,0.03)',  label: '#047857' },
    'ai-ml':     { border: '#6d28d9', floor: 'rgba(109,40,217,0.03)', label: '#6d28d9' },
    domain:      { border: '#be123c', floor: 'rgba(190,18,60,0.03)', label: '#be123c' },
    engineering: { border: '#c2410c', floor: 'rgba(194,65,12,0.03)', label: '#c2410c' },
    research:    { border: '#0369a1', floor: 'rgba(3,105,161,0.03)', label: '#0369a1' },
    meeting:     { border: '#1a1a1a', floor: 'rgba(26,26,26,0.02)',  label: '#1a1a1a' },
    'boss-room': { border: '#b45309', floor: 'rgba(180,83,9,0.03)',  label: '#b45309' },
    'tea-room':  { border: '#047857', floor: 'rgba(4,120,87,0.03)',  label: '#047857' },
    'game-room': { border: '#be123c', floor: 'rgba(190,18,60,0.03)', label: '#be123c' },
  },
}

// ── 所有可用主題 ────────────────────────────────────────────

export const ALL_THEMES: WindAITheme[] = [
  defaultTheme,
  darkForest,
  darkOcean,
  lightClean,
  modernCorporate,
  minimalWhiteboard,
]

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
