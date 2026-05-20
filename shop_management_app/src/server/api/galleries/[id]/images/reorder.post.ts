// Reorder images in gallery
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
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot reorder images' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)

    if (!galleryId || isNaN(galleryId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery ID' })
    }

    const body = await readBody(event)
    const { order } = body

    if (!Array.isArray(order) || order.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'order array is required' })
    }

    // Check if user owns the gallery
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

    // Update display order for each image
    const updates = order.map((imageId: number, index: number) => {
      return db.update(galleryImages)
        .set({ displayOrder: index + 1 })
        .where(and(
          eq(galleryImages.id, imageId),
          eq(galleryImages.galleryId, galleryId)
        ))
    })

    if (updates.length > 0) {
      await db.transaction(async (txn) => {
        for (const update of updates) {
          await update
        }
      })
    }

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[reorder-gallery-images] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to reorder images',
    })
  }
})
