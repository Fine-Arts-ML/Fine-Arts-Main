// Theme type
export type Theme = 'light' | 'dark'

export function useTheme() {
  // Use Nuxt's useState for SSR-safe state sharing
  // The key 'theme' ensures all components share the same state
  const theme = useState<Theme>('theme', () => {
    // Default value (used during SSR)
    return 'light'
  })

  // Apply theme to document
  function applyTheme(t: Theme) {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', t === 'dark')
      document.documentElement.setAttribute('data-theme', t)
    }
    localStorage.setItem('theme', t)
  }

  // Toggle theme
  function toggleTheme() {
    applyTheme(theme.value === 'light' ? 'dark' : 'light')
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      if (!localStorage.getItem('theme')) {
        const newTheme = e.matches ? 'dark' : 'light'
        applyTheme(newTheme)
        theme.value = newTheme
      }
    })
  }

  return {
    theme,
    applyTheme,
    toggleTheme,
  }
}
