// Auth Plugin
// Initializes authentication state on app load

import { useAuth } from '~/composables/useAuth'

export default defineNuxtPlugin(() => {
  const { checkSession } = useAuth()

  // Check session on app initialization
  if (typeof window !== 'undefined') {
    checkSession().catch((error) => {
      console.error('[auth-plugin] Failed to check session:', error)
    })
  }
})
