// Admin Middleware
// Ensures the current user has admin role
// Excludes public routes and seed-admin endpoint
// Note: This middleware runs after auth.ts middleware

export default defineEventHandler(async (event) => {
  // Public routes that don't require admin check
  const publicPaths = [
    '/api/auth/seed-admin', // Initial setup endpoint
    '/login',               // Login page
    '/_nuxt/',              // Static assets
    '/api/files/preview-proxy/', // Preview proxy
    '/api/settings/rag-models',  // RAG models list (public)
  ]

  // Skip admin check for public paths
  const path = event.path
  if (publicPaths.some(p => path.startsWith(p))) {
    return
  }

  // If user is not set (auth middleware hasn't run or user not authenticated),
  // let auth middleware handle the 401/redirect
  const user = event.context.user as any
  if (!user) {
    return // Let auth middleware handle this
  }

  if (user.role !== 'admin') {
    throw createError({ 
      statusCode: 403, 
      statusMessage: 'Admin access required' 
    })
  }
})
