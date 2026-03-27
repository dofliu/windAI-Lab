/**
 * ThemeProvider — 主題 React Context。
 *
 * 在應用最外層包裹 <ThemeProvider>，所有子元件
 * 即可透過 useTheme() 存取目前主題並切換。
 *
 * 主題選擇透過 localStorage 持久化。
 */

import { createContext, useContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { type WindAITheme, defaultTheme, applyThemeToRoot, ALL_THEMES } from './theme'

const THEME_STORAGE_KEY = 'windai_theme_id'

interface ThemeContextValue {
  /** 當前主題 */
  theme: WindAITheme
  /** 切換主題 */
  setTheme: (theme: WindAITheme) => void
  /** 當前主題 ID */
  themeId: string
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: defaultTheme,
  setTheme: () => {},
  themeId: defaultTheme.id,
})

interface ThemeProviderProps {
  children: ReactNode
  /** 初始主題（預設從 localStorage 讀取，回退到 defaultTheme） */
  initialTheme?: WindAITheme
}

function loadSavedTheme(): WindAITheme {
  try {
    const savedId = localStorage.getItem(THEME_STORAGE_KEY)
    if (savedId) {
      const found = ALL_THEMES.find((t) => t.id === savedId)
      if (found) return found
    }
  } catch {
    // localStorage 不可用
  }
  return defaultTheme
}

export function ThemeProvider({ children, initialTheme }: ThemeProviderProps) {
  const [theme, setThemeState] = useState<WindAITheme>(initialTheme ?? loadSavedTheme)

  const setTheme = useCallback((newTheme: WindAITheme) => {
    setThemeState(newTheme)
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme.id)
    } catch {
      // quota exceeded
    }
  }, [])

  // 當主題變更時，注入 CSS custom properties
  useEffect(() => {
    applyThemeToRoot(theme)
  }, [theme])

  const value = useMemo(
    () => ({ theme, setTheme, themeId: theme.id }),
    [theme, setTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

/** 取得當前主題 */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext)
}
