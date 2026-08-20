// Update image order in gallery (caption management moved to /api/galleries/[galleryId]/images/[imageId]/captions)
import { db } from '~/lib/db'
import { galleryImages, galleries } from '~/lib/gallery-schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot update images' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)

    if (!galleryId || !imageId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or image ID' })
    }

    const body = await readBody(event)
    const { displayOrder } = body

    // Check gallery ownership
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

    const updateData: Record<string, any> = {}
    if (displayOrder !== undefined) updateData.displayOrder = displayOrder

    if (Object.keys(updateData).length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'No valid fields to update' })
    }

    const updated = await db.update(galleryImages)
      .set(updateData)
      .where(and(
        eq(galleryImages.id, imageId),
        eq(galleryImages.galleryId, galleryId)
      ))
      .returning()

    if (!updated[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Image not found in gallery' })
    }

    return {
      id: updated[0].id,
      galleryId: updated[0].galleryId,
      fileId: updated[0].fileId,
      displayOrder: updated[0].displayOrder,
      captions: [],
      addedById: updated[0].addedById,
      addedAt: updated[0].addedAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[update-gallery-image] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to update image' })
  }
})
