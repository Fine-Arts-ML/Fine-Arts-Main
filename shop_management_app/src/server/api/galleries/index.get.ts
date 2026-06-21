// List all galleries (filtered by user role)
import { db } from '~/lib/db'
import { galleries, galleryAccess, galleryImages } from '~/lib/gallery-schema'
import { userAccounts } from '~/lib/auth-schema'
import { eq, and, asc, or, exists, sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    // Fetch galleries based on role
    let galleryList: any[]
    
    if (user.role === 'admin') {
      galleryList = await db.select({
        id: galleries.id,
        name: galleries.name,
        description: galleries.description,
        createdById: galleries.createdById,
        updatedById: galleries.updatedById,
        isActive: galleries.isActive,
        createdAt: galleries.createdAt,
        updatedAt: galleries.updatedAt,
      }).from(galleries)
        .orderBy(asc(galleries.createdAt))
    } else if (user.role === 'user') {
      galleryList = await db.select({
        id: galleries.id,
        name: galleries.name,
        description: galleries.description,
        createdById: galleries.createdById,
        updatedById: galleries.updatedById,
        isActive: galleries.isActive,
        createdAt: galleries.createdAt,
        updatedAt: galleries.updatedAt,
      }).from(galleries)
        .where(and(
          eq(galleries.isActive, true),
          or(eq(galleries.createdById, user.id), exists(
            db.select({ id: galleryAccess.galleryId }).from(galleryAccess).where(eq(galleryAccess.guestUserId, user.id))
          ))
        ))
        .orderBy(asc(galleries.createdAt))
    } else {
      galleryList = await db.select({
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

    // Fetch image counts for all galleries in one query
    const imageCountsResult = await db.select({
      galleryId: galleryImages.galleryId,
      count: sql<number>`COUNT(*)`.mapWith(Number),
    }).from(galleryImages)
      .groupBy(galleryImages.galleryId)

    // Build a map of galleryId -> count
    const imageCountMap = new Map<number, number>()
    for (const row of imageCountsResult) {
      imageCountMap.set(row.galleryId, row.count)
    }

    // Combine galleries with their image counts
    return galleryList.map(g => ({
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
    console.error('[list-galleries] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch galleries',
    })
  }
})
