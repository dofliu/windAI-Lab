/**
 * WindAI Lab API 設定 — 統一管理後端 URL，不再硬編碼 port。
 *
 * 優先級：
 * 1. 環境變數 VITE_API_BASE（部署時設定）
 * 2. 相對路徑（Vite proxy 模式，開發時推薦）
 *
 * Vite proxy 會將 /api/* 和 /ws 轉發至後端，
 * 因此前端只需用相對路徑即可。
 */

/** HTTP API base URL（不含尾部 /） */
export const API_BASE: string =
  import.meta.env.VITE_API_BASE || '/api'

/** WebSocket URL */
export const WS_URL: string =
  import.meta.env.VITE_WS_URL ||
  `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
