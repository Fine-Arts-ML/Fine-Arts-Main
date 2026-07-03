/**
 * Guest Route Middleware
 * Protects admin/user routes from guest access.
 * Guests are redirected to /guest (the guest portal).
 * Registered as a global middleware (guest.global.ts).
 */

export default defineNuxtRouteMiddleware(async (to, from) => {
  const { user, isGuest, checkSession } = useAuth()

  const currentPath = to.path

  // Ensure auth state is loaded before making routing decisions
  if (!user.value) {
    try {
      await checkSession()
    } catch (e) {
      console.error('[guest-middleware] Session check failed:', e)
    }
  }

  // If still no user after check, redirect to login
  // But don't redirect if already on login page (avoid infinite loop)
  if (!user.value && currentPath !== '/login') {
    return navigateTo('/login')
  }

  // If user is authenticated but not a guest, allow all routes
  if (user.value && !isGuest.value) {
    return
  }

  // If user is not authenticated and not on login page, redirect to login
  if (!user.value && currentPath !== '/login') {
    return navigateTo('/login')
  }

  // Only apply guest restrictions if user is authenticated as guest
  if (!user.value || !isGuest.value) {
    return
  }

  // Allowed routes for guests: guest portal, gallery viewer, login, root
  const allowedPaths = ['/guest', '/gallery', '/login', '/']

  // Check if current path is allowed for guests
  const isAllowed = allowedPaths.some((path) => {
    if (path === '/') return currentPath === '/' || currentPath === ''
    if (path === '/gallery') return currentPath.startsWith('/gallery')
    return currentPath === path
  })

  if (!isAllowed) {
    return navigateTo('/guest')
  }
})
