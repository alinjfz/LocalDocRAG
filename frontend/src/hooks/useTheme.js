import { useCallback, useEffect, useState } from 'react'

export function useTheme() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem('localdocrag-theme') || 'dark',
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('localdocrag-theme', theme)
  }, [theme])

  const toggleTheme = useCallback(
    () => setTheme((t) => (t === 'dark' ? 'light' : 'dark')),
    [],
  )

  return { theme, toggleTheme }
}
