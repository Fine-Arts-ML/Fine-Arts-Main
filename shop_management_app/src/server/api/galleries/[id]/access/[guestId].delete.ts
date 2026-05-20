// Revoke guest access to a gallery
import { db } from '~/lib/db'
import { galleryAccess, galleries } from '~/lib/gallery-schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot revoke access' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const guestId = parseInt(getRouterParam(event, 'guestId') || '0', 10)

    if (!galleryId || !guestId || isNaN(galleryId) || isNaN(guestId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or guest ID' })
    }

    // Check gallery ownership
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    if (user.role !== 'admin' && galleryResult[0].createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to manage this gallery' })
    }

    // Revoke access
    await db.delete(galleryAccess)
      .where(and(
        eq(galleryAccess.galleryId, galleryId),
        eq(galleryAccess.guestUserId, guestId)
      ))

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[revoke-gallery-access] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to revoke access' })
  }
})
