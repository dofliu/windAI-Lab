/**
 * ThemeProvider — 主題 React Context。
 *
 * 在應用最外層包裹 <ThemeProvider>，所有子元件
 * 即可透過 useTheme() 存取目前主題並切換。
 */

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { type WindAITheme, defaultTheme, applyThemeToRoot } from './theme'

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
  /** 初始主題（預設使用 defaultTheme） */
  initialTheme?: WindAITheme
}

export function ThemeProvider({ children, initialTheme }: ThemeProviderProps) {
  const [theme, setTheme] = useState<WindAITheme>(initialTheme ?? defaultTheme)

  // 當主題變更時，注入 CSS custom properties
  useEffect(() => {
    applyThemeToRoot(theme)
  }, [theme])

  const value = useMemo(
    () => ({ theme, setTheme, themeId: theme.id }),
    [theme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

/** 取得當前主題 */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext)
}
