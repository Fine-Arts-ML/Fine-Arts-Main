/**
 * Middleware that allows authenticated users (admin + user) but blocks guests.
 * Applied to all Tags & Tagging pipeline pages.
 */
import { useAuth } from '~/composables/useAuth'

export default defineNuxtRouteMiddleware((to, from) => {
  const { isAuthenticated, user } = useAuth()
  
  if (!isAuthenticated.value) {
    return navigateTo('/login')
  }
  
  // Guests should not access this section - redirect to guest portal
  if (user.value?.role === 'guest') {
    return navigateTo('/guest')
  }
})
