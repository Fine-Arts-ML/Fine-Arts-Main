// Get galleries accessible to current user (for guests)
import { db } from '~/lib/db'
import { galleries, galleryAccess } from '~/lib/gallery-schema'
import { eq, and, asc } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)

    // Guests get their accessible galleries
    if (user.role === 'guest') {
      const accessibleGalleries = await db.select({
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

      return accessibleGalleries.map(g => ({
        id: g.id,
        name: g.name,
        description: g.description,
        createdById: g.createdById,
        updatedById: g.updatedById,
        isActive: g.isActive,
        createdAt: g.createdAt.toISOString(),
        updatedAt: g.updatedAt.toISOString(),
      }))
    }

    // For non-guests, return all active galleries
    const activeGalleries = await db.select({
      id: galleries.id,
      name: galleries.name,
      description: galleries.description,
      createdById: galleries.createdById,
      updatedById: galleries.updatedById,
      isActive: galleries.isActive,
      createdAt: galleries.createdAt,
      updatedAt: galleries.updatedAt,
    }).from(galleries)
      .where(eq(galleries.isActive, true))
      .orderBy(asc(galleries.name))

    return activeGalleries.map(g => ({
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
    console.error('[get-my-galleries] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to fetch galleries' })
  }
})
