// Theme plugin - runs before Vue app creation to sync theme from DOM/localStorage
export default defineNuxtPlugin((nuxtApp) => {
  // This runs on both SSR and client, but we only care about client-side
  if (typeof window !== 'undefined') {
    // Get the theme that was applied by the inline script
    const isDark = document.documentElement.classList.contains('dark')
    const theme = isDark ? 'dark' : 'light'
    
    // Force the theme into localStorage if not already there
    if (!localStorage.getItem('theme')) {
      localStorage.setItem('theme', theme)
    }
    
    // Log for debugging
    console.log('[theme plugin] Initial theme:', theme, 'isDark:', isDark)
  }
})
