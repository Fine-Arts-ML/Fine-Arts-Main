// Auth Middleware
// Protects routes and attaches user info to event context

import { eq } from 'drizzle-orm'
import { userAccounts } from '~/lib/auth-schema'
import { getDb } from '~/lib/db'

export default defineEventHandler(async (event) => {
  const path = event.path
  
  // Public routes that don't require authentication
  const publicPaths = [
    '/api/auth/',
    '/login',
    '/api/files/preview-proxy/',
    '/api/settings/rag-models',
    '/_nuxt/',
  ]

  // Check if path is public
  const isPublic = publicPaths.some(p => path.startsWith(p))
  
  // API routes under /api/ (except public ones) require auth
  // Frontend pages (except /login) require auth
  const isApiRoute = path.startsWith('/api/') && !isPublic
  const isFrontendPage = !path.startsWith('/api/') && path !== '/login' && !path.startsWith('/_nuxt')

  if (isApiRoute || isFrontendPage) {
    // getUserSession is auto-imported by nuxt-auth-utils
    const session = await getUserSession(event)
    
    if (!session?.user?.id) {
      // Return 401 for API routes
      if (isApiRoute) {
        throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
      }
      
      // Redirect to login for frontend pages
      if (event.node.res.writableEnded) {
        return
      }
      
      return sendRedirect(event, '/login')
    }

    // Get user account details and attach to context
    const db = getDb()
    const appUsers = await db
      .select()
      .from(userAccounts)
      .where(eq(userAccounts.id, session.user.id))
      .limit(1)

    if (!appUsers.length || !appUsers[0].isActive) {
      await clearUserSession(event)
      
      if (isApiRoute) {
        throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
      }
      
      return sendRedirect(event, '/login')
    }

    const appUser = appUsers[0]
    event.context.user = {
      id: appUser.id,
      nextcloudUid: appUser.nextcloudUid,
      role: appUser.role,
      allowedGalleryIds: appUser.allowedGalleryIds || [],
    } as any
  }
})
