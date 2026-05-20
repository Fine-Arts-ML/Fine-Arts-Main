// Remove image from gallery
import { db } from '~/lib/db'
import { galleryImages, galleryAccess, galleries } from '~/lib/gallery-schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot remove images from galleries' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)

    if (!galleryId || !imageId || isNaN(galleryId) || isNaN(imageId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or image ID' })
    }

    // Check if user owns the gallery
    const { userAccounts } = await import('~/lib/auth-schema')
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    if (user.role !== 'admin' && galleryResult[0].createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to modify this gallery' })
    }

    // Delete the image from gallery
    await db.delete(galleryImages)
      .where(and(
        eq(galleryImages.id, imageId),
        eq(galleryImages.galleryId, galleryId)
      ))

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[remove-gallery-image] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to remove image from gallery',
    })
  }
})
