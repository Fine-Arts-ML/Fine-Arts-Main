// List all galleries (filtered by user role)
import { db } from '~/lib/db'
import { galleries, galleryAccess, galleryImages } from '~/lib/gallery-schema'
import { userAccounts } from '~/lib/auth-schema'
import { eq, and, asc, count } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    let query = db.select().from(galleries)

    // Filter by role
    if (user.role === 'admin') {
      // Admins see all galleries
      query = query.orderBy(asc(galleries.createdAt))
    } else if (user.role === 'user') {
      // Regular users see their own galleries and shared ones
      query = query.where(and(
        eq(galleries.isActive, true),
        or(eq(galleries.createdById, user.id), exists(
          db.select({ id: galleryAccess.galleryId }).from(galleryAccess).where(eq(galleryAccess.guestUserId, user.id))
        ))
      )).orderBy(asc(galleries.createdAt))
    } else {
      // Guests see only galleries assigned to them
      query = db.select({
        id: galleries.id,
        name: galleries.name,
        description: galleries.description,
        createdById: galleries.createdById,
        updatedById: galleries.updatedById,
        isActive: galleries.isActive,
        createdAt: galleries.createdAt,
        updatedAt: galleries.updatedAt,
      }).from(galleries)
        .innerJoin(galleryAccess, eq(galleries.id, galleryAccess.galleryId))
        .where(and(
          eq(galleries.isActive, true),
          eq(galleryAccess.guestUserId, user.id)
        ))
        .orderBy(asc(galleries.name))
    }

    const result = await query

    return result.map(g => ({
      id: g.id,
      name: g.name,
      description: g.description,
      createdById: g.createdById,
      updatedById: g.updatedById,
      isActive: g.isActive,
      createdAt: g.createdAt.toISOString(),
      updatedAt: g.updatedAt.toISOString(),
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[list-galleries] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch galleries',
    })
  }
})
