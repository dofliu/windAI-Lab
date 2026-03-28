/**
 * OfficeRenderer 抽象層 — 定義辦公室視圖的可插拔介面。
 *
 * 每個 renderer 實作一個完全獨立的視覺風格（像素風、現代風、極簡風等），
 * 而非只是換色。App.tsx 透過 registry 動態取得目前的 renderer，
 * 不需要知道底層實作細節。
 */

import { type ComponentType } from 'react'
import { type Agent, type OfficeRoom, type SpeechBubble } from '../types/agent'

// ── 辦公室主視圖 Props（展開模式）──────────────────────────

export interface OfficeViewProps {
  rooms: OfficeRoom[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
  speechBubbles: SpeechBubble[]
  isWarRoomActive?: boolean
}

// ── 側邊欄收合模式 Props ──────────────────────────────────

export interface CompactViewProps {
  agents: Agent[]
  selectedAgent: Agent | null
  onSelectAgent: (agent: Agent) => void
  collapsed: boolean
}

// ── Renderer 定義 ─────────────────────────────────────────

export interface OfficeRendererDefinition {
  /** 唯一 ID，對應主題的 visualStyle */
  id: string
  /** 顯示名稱 */
  name: string
  /** 簡短描述 */
  description: string
  /** 預覽圖示（emoji 或文字） */
  icon: string
  /** 展開模式的辦公室元件 */
  OfficeView: ComponentType<OfficeViewProps>
  /** 收合模式的側邊欄元件 */
  CompactView: ComponentType<CompactViewProps>
  /** 切換到像素模式的最小寬度，若為 0 表示無門檻 */
  minExpandWidth: number
}
