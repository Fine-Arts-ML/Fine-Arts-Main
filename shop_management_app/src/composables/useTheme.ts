// Theme type
export type Theme = 'light' | 'dark' | 'auto'

export function useTheme() {
  // Use Nuxt's useState for SSR-safe state sharing
  // The key 'theme' ensures all components share the same state
  const theme = useState<Theme>('theme', () => {
    // Default value (used during SSR)
    return 'auto'
  })

  // Sync from localStorage on client-side hydration
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('theme')
    if (saved === 'light' || saved === 'dark' || saved === 'auto') {
      theme.value = saved as Theme
    }
  }

  // Apply theme to document
  function applyTheme(t: Theme) {
    if (typeof document !== 'undefined') {
      const isDark = t === 'auto'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
        : t === 'dark'
      document.documentElement.classList.toggle('dark', isDark)
      document.documentElement.setAttribute('data-theme', t)
    }
    localStorage.setItem('theme', t)
  }

  // Toggle theme through all three modes: light -> dark -> auto -> light
  function toggleTheme() {
    const cycle: Theme[] = ['light', 'dark', 'auto']
    const currentIndex = cycle.indexOf(theme.value as Theme)
    const nextIndex = (currentIndex + 1) % cycle.length
    applyTheme(cycle[nextIndex]!)
    theme.value = cycle[nextIndex]!
  }

  // Get the resolved visual theme (what is currently displayed)
  function getResolvedTheme(): 'light' | 'dark' {
    // SSR guard: window is not available during server-side rendering
    if (typeof window === 'undefined') {
      return 'light'
    }
    if (theme.value === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return theme.value as 'light' | 'dark'
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    mediaQuery.addEventListener('change', (e) => {
      if (theme.value === 'auto') {
        applyTheme('auto') // Re-apply to resolve auto with new system preference
        theme.value = 'auto'
      }
    })
  }

  return {
    theme,
    applyTheme,
    toggleTheme,
    getResolvedTheme,
  }
}
