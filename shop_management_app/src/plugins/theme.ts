// Theme plugin - runs before Vue app creation to sync theme from DOM/localStorage
export default defineNuxtPlugin((nuxtApp) => {
  // This runs on both SSR and client, but we only care about client-side
  if (typeof window !== 'undefined') {
    // Ensure localStorage has a valid theme value
    const saved = localStorage.getItem('theme')
    if (saved !== 'light' && saved !== 'dark' && saved !== 'auto') {
      localStorage.setItem('theme', 'auto')
    }
    
    // Log for debugging
    console.log('[theme plugin] Initial theme:', localStorage.getItem('theme'))
  }
})
