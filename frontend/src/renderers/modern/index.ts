/**
 * Modern Office Renderer — 現代企業風格辦公室。
 *
 * Glassmorphism + 大圓角 + 光暈效果，
 * 與像素風格截然不同的視覺體驗。
 */

import ModernOfficeView from './ModernOfficeView'
import ModernCompactView from './ModernCompactView'
import { type OfficeRendererDefinition } from '../types'

export const modernRenderer: OfficeRendererDefinition = {
  id: 'modern',
  name: '現代企業',
  description: '毛玻璃卡片 + 圓形 Avatar + 光暈動效',
  icon: '◉',
  OfficeView: ModernOfficeView,
  CompactView: ModernCompactView,
  minExpandWidth: 400,
}
