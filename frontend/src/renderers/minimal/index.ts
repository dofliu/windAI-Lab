/**
 * Minimal Office Renderer — 極簡白板風格。
 *
 * 手繪虛線框 + 文字為主 + 大留白，
 * 類似 Excalidraw / 白板筆記的視覺感受。
 */

import MinimalOfficeView from './MinimalOfficeView'
import MinimalCompactView from './MinimalCompactView'
import { type OfficeRendererDefinition } from '../types'

export const minimalRenderer: OfficeRendererDefinition = {
  id: 'minimal',
  name: '極簡白板',
  description: '手繪虛線框 + 純文字 + 大留白',
  icon: '◻',
  OfficeView: MinimalOfficeView,
  CompactView: MinimalCompactView,
  minExpandWidth: 350,
}
