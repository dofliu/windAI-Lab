export type { OfficeRendererDefinition, OfficeViewProps, CompactViewProps } from './types'
export { registerRenderer, getRenderer, getAllRenderers, getDefaultRenderer } from './registry'

// ── 註冊所有內建 renderer ─────────────────────────────────
import { registerRenderer } from './registry'
import { pixelRenderer } from './pixel'
import { modernRenderer } from './modern'
import { minimalRenderer } from './minimal'

registerRenderer(pixelRenderer)
registerRenderer(modernRenderer)
registerRenderer(minimalRenderer)
