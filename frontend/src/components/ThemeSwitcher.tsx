/**
 * ThemeSwitcher — 主題切換下拉選單。
 *
 * 放在 Header 右側，以色塊形式顯示可選主題。
 */

import { useState, useRef, useEffect } from 'react'
import { useTheme, ALL_THEMES } from '../themes'

export default function ThemeSwitcher() {
  const { theme, setTheme } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // 點擊外部關閉
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

  return (
    <div className="relative" ref={ref}>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[10px] transition-colors hover:brightness-125"
        style={{
          backgroundColor: theme.global.border + '40',
          color: theme.global.textSecondary,
        }}
        title="切換主題"
      >
        <div
          className="w-3 h-3 rounded-full border"
          style={{
            backgroundColor: theme.global.accent,
            borderColor: theme.global.border,
          }}
        />
        <span>{theme.name}</span>
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
          className="absolute right-0 top-full mt-1 z-50 rounded-lg border shadow-lg py-1 min-w-[140px]"
          style={{
            backgroundColor: theme.global.panelBg,
            borderColor: theme.global.border,
          }}
        >
          {ALL_THEMES.map((t) => {
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
                </div>
                <span className="flex-1 text-left">{t.name}</span>
                {isActive && (
                  <span style={{ color: theme.global.accent }}>✓</span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
