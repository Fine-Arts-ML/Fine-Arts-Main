// DELETE /api/galleries/[id]/images/[imageId]/captions/[captionId]
// Removes the caption link from a gallery image (does not delete from global pool)

import { db } from '~/lib/db'
import { galleryImageCaptions, galleryImages, galleries } from '~/lib/gallery-schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot delete captions' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)
    const captionId = parseInt(getRouterParam(event, 'captionId') || '0', 10)

    if (!galleryId || !imageId || !captionId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery, image, or caption ID' })
    }

    // Check gallery access
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    // Check if user owns the gallery or is admin
    if (user.role !== 'admin' && galleryResult[0].createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to modify this gallery' })
    }

    // Verify the caption link exists for this image
    const captionCheck = await db.select()
      .from(galleryImageCaptions)
      .where(and(
        eq(galleryImageCaptions.captionId, captionId),
        eq(galleryImageCaptions.galleryImageId, imageId)
      ))
      .limit(1)

    if (!captionCheck[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Caption not found for this image' })
    }

    // Delete only the link (not the caption from global pool)
    await db.delete(galleryImageCaptions)
      .where(and(
        eq(galleryImageCaptions.captionId, captionId),
        eq(galleryImageCaptions.galleryImageId, imageId)
      ))

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[delete-caption] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to delete caption' })
  }
})
