/**
 * OfficeRenderer Registry — 管理所有可用的辦公室視圖 renderer。
 *
 * 新增一個全新風格只需：
 * 1. 建立一個新的 OfficeRendererDefinition
 * 2. 在此 registry 註冊
 * 3. 在 theme 中指定 visualStyle 即可
 */

import { type OfficeRendererDefinition } from './types'

const renderers = new Map<string, OfficeRendererDefinition>()

/** 註冊一個 renderer */
export function registerRenderer(renderer: OfficeRendererDefinition): void {
  renderers.set(renderer.id, renderer)
}

/** 根據 ID 取得 renderer */
export function getRenderer(id: string): OfficeRendererDefinition | undefined {
  return renderers.get(id)
}

/** 取得所有已註冊的 renderer */
export function getAllRenderers(): OfficeRendererDefinition[] {
  return Array.from(renderers.values())
}

/** 取得預設 renderer（第一個註冊的） */
export function getDefaultRenderer(): OfficeRendererDefinition | undefined {
  return renderers.values().next().value
}
