/**
 * ThemeSwitcher — 主題 + 視覺風格切換面板。
 *
 * 依 visualStyle 分組顯示主題，讓使用者一目了然
 * 切換主題同時會切換辦公室的 renderer 風格。
 */

import { useState, useRef, useEffect, useMemo } from 'react'
import { useTheme, ALL_THEMES } from '../themes'
import { getAllRenderers } from '../renderers'

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const renderers = getAllRenderers()
  const rendererMap = useMemo(() => {
    const m = new Map<string, { name: string; icon: string }>()
    renderers.forEach((r) => m.set(r.id, { name: r.name, icon: r.icon }))
    return m
  }, [renderers])

  // 依 visualStyle 分組
  const grouped = useMemo(() => {
    const groups = new Map<string, typeof ALL_THEMES>()
    ALL_THEMES.forEach((t) => {
      const key = t.visualStyle
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(t)
    })
    return Array.from(groups.entries())
  }, [])

  const currentRenderer = rendererMap.get(theme.visualStyle)

  return (
    <div className="relative" ref={ref}>
      {/* Trigger */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px] transition-colors hover:brightness-125"
        style={{
          backgroundColor: theme.global.border + '40',
          color: theme.global.textSecondary,
        }}
        title="切換主題與風格"
      >
        <div
          className="w-3 h-3 rounded-full border"
          style={{
            backgroundColor: theme.global.accent,
            borderColor: theme.global.border,
          }}
        />
        <span>{theme.name}</span>
        {currentRenderer && (
          <span style={{ color: theme.global.textMuted }}>{currentRenderer.icon}</span>
        )}
        <svg
          className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-full mt-1 z-50 rounded-lg border shadow-xl py-2 min-w-[200px]"
          style={{
            backgroundColor: theme.global.panelBg,
            borderColor: theme.global.border,
          }}
        >
          {grouped.map(([styleId, themes]) => {
            const renderer = rendererMap.get(styleId)
            return (
              <div key={styleId}>
                {/* 風格分組標題 */}
                <div
                  className="flex items-center gap-1.5 px-3 py-1.5 mt-1 first:mt-0"
                  style={{ color: theme.global.textMuted }}
                >
                  <span className="text-[9px]">{renderer?.icon ?? '●'}</span>
                  <span className="text-[9px] uppercase tracking-wider font-medium">
                    {renderer?.name ?? styleId}
                  </span>
                  <div
                    className="flex-1 border-b ml-1"
                    style={{ borderColor: theme.global.border + '60' }}
                  />
                </div>

                {/* 該風格下的主題 */}
                {themes.map((t) => {
                  const isActive = t.id === theme.id
                  return (
                    <button
                      key={t.id}
                      onClick={() => {
                        setTheme(t)
                        setOpen(false)
                      }}
                      className="w-full flex items-center gap-2 px-3 py-1.5 text-[11px] transition-colors hover:brightness-125"
                      style={{
                        backgroundColor: isActive ? theme.global.accent + '15' : 'transparent',
                        color: isActive ? theme.global.accent : theme.global.textSecondary,
                      }}
                    >
                      {/* 色塊預覽 */}
                      <div className="flex gap-0.5">
                        <div
                          className="w-2.5 h-2.5 rounded-sm"
                          style={{ backgroundColor: t.global.pageBg, border: `1px solid ${t.global.border}` }}
                        />
                        <div
                          className="w-2.5 h-2.5 rounded-sm"
                          style={{ backgroundColor: t.global.accent }}
                        />
                        <div
                          className="w-2.5 h-2.5 rounded-sm"
                          style={{ backgroundColor: t.tiers['ai-ml']?.primary ?? t.global.accent }}
                        />
                      </div>
                      <span className="flex-1 text-left">{t.name}</span>
                      {t.isDark ? (
                        <span className="text-[8px]" style={{ color: theme.global.textMuted }}>dark</span>
                      ) : (
                        <span className="text-[8px]" style={{ color: theme.global.textMuted }}>light</span>
                      )}
                      {isActive && (
                        <span style={{ color: theme.global.accent }}>✓</span>
                      )}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
