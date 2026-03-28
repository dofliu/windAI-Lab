/**
 * Pixel Office Renderer — 像素風格辦公室。
 *
 * 封裝原有的 OfficeWorld（像素動畫）和 CompactOffice（收合列表）
 * 為可插拔的 renderer。
 */

import OfficeWorld from '../../components/OfficeWorld'
import CompactOffice from '../../components/CompactOffice'
import { type OfficeRendererDefinition } from '../types'

export const pixelRenderer: OfficeRendererDefinition = {
  id: 'pixel',
  name: '像素辦公室',
  description: '復古像素風格，角色會走動、對話',
  icon: '🎮',
  OfficeView: OfficeWorld,
  CompactView: CompactOffice,
  minExpandWidth: 550,
}
