// Get galleries accessible to current user (for guests)
import { db } from '~/lib/db'
import { galleries, galleryAccess, galleryImages } from '~/lib/gallery-schema'
import { eq, and, asc, inArray, sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

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

      // Fetch image counts for these galleries using inArray for proper parameterization
      const galleryIds = accessibleGalleries.map((g: any) => g.id)
      const imageCountMap = new Map<number, number>()

      if (galleryIds.length > 0) {
        const imageCountsResult = await db.select({
          galleryId: galleryImages.galleryId,
          count: sql<number>`COUNT(*)`.mapWith(Number),
        }).from(galleryImages)
          .where(inArray(galleryImages.galleryId, galleryIds))
          .groupBy(galleryImages.galleryId)

        for (const row of imageCountsResult) {
          imageCountMap.set(row.galleryId, row.count)
        }
      }

      return accessibleGalleries.map(g => ({
        id: g.id,
        name: g.name,
        description: g.description,
        createdById: g.createdById,
        updatedById: g.updatedById,
        isActive: g.isActive,
        createdAt: g.createdAt.toISOString(),
        updatedAt: g.updatedAt.toISOString(),
        imageCount: imageCountMap.get(g.id) ?? 0,
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

    // Fetch image counts for all active galleries
    const galleryIds = activeGalleries.map((g: any) => g.id)
    const imageCountMap = new Map<number, number>()

    if (galleryIds.length > 0) {
      const imageCountsResult = await db.select({
        galleryId: galleryImages.galleryId,
        count: sql<number>`COUNT(*)`.mapWith(Number),
      }).from(galleryImages)
        .where(inArray(galleryImages.galleryId, galleryIds))
        .groupBy(galleryImages.galleryId)

      for (const row of imageCountsResult) {
        imageCountMap.set(row.galleryId, row.count)
      }
    }

    return activeGalleries.map(g => ({
      id: g.id,
      name: g.name,
      description: g.description,
      createdById: g.createdById,
      updatedById: g.updatedById,
      isActive: g.isActive,
      createdAt: g.createdAt.toISOString(),
      updatedAt: g.updatedAt.toISOString(),
      imageCount: imageCountMap.get(g.id) ?? 0,
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-my-galleries] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to fetch galleries' })
  }
})
