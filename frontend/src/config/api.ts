/**
 * WindAI Lab API 設定 — 統一管理後端 URL。
 *
 * 連線策略（依優先級）：
 * 1. 環境變數 VITE_API_BASE / VITE_WS_URL（部署時設定）
 * 2. Vite proxy 模式：相對路徑（port 5173 dev server）
 * 3. 同主機推算：自動連 localhost:BACKEND_PORT（非 proxy 模式）
 */

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '5800'

/**
 * 判斷是否在 Vite dev server 下運行（有 proxy 可用）。
 * Vite proxy 會把 /api/* 和 /ws 轉發至後端。
 */
function hasProxy(): boolean {
  return window.location.port === '5173'
}

/**
 * 取得後端 origin（含 protocol + host + port，不含尾部 /）。
 * 在 proxy 模式下回傳空字串（用相對路徑即可）。
 */
function getBackendOrigin(): string {
  if (import.meta.env.VITE_API_BASE) {
    // 使用者指定了完整 base → 取出 origin 部分
    const base = import.meta.env.VITE_API_BASE as string
    return base.replace(/\/api\/?$/, '')
  }
  if (hasProxy()) {
    return ''  // proxy 模式，相對路徑
  }
  return `http://${window.location.hostname}:${BACKEND_PORT}`
}

/** 後端 origin（proxy 模式為空） */
export const BACKEND_ORIGIN: string = getBackendOrigin()

/** HTTP API base URL（不含尾部 /） */
export const API_BASE: string = `${BACKEND_ORIGIN}/api`

/** WebSocket URL */
export const WS_URL: string = (() => {
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL as string
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  if (hasProxy()) {
    return `${proto}//${window.location.host}/ws`
  }
  return `${proto}//${window.location.hostname}:${BACKEND_PORT}/ws`
})()
