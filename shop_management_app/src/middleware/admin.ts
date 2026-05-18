// Admin Route Middleware
// Protects routes that require admin role

export default defineNuxtRouteMiddleware((to, from) => {
  const { user, isAuthenticated } = useAuth()
  
  // Wait for auth to load
  if (!isAuthenticated.value || !user.value) {
    return navigateTo('/login')
  }
  
  // Check admin role
  if (user.value.role !== 'admin') {
    return navigateTo('/access-denied')
  }
})
