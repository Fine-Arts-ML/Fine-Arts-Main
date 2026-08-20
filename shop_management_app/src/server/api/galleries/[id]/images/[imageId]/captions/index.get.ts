// GET /api/galleries/[id]/images/[imageId]/captions
// Returns all captions linked to a specific gallery image (joins with global caption pool)

import { db } from '~/lib/db'
import { galleryImageCaptions, galleryImages, galleries, galleryAccess, captions } from '~/lib/gallery-schema'
import { eq, and, asc } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)

    if (!galleryId || !imageId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or image ID' })
    }

    // Check access for guests
    if (user.role === 'guest') {
      const accessCheck = await db.select()
        .from(galleryAccess)
        .where(and(
          eq(galleryAccess.galleryId, galleryId),
          eq(galleryAccess.guestUserId, user.id)
        ))
        .limit(1)
      
      if (!accessCheck[0]) {
        throw createError({ statusCode: 403, statusMessage: 'You do not have access to this gallery' })
      }
    }

    // Verify the image belongs to this gallery
    const imageCheck = await db.select()
      .from(galleryImages)
      .where(and(
        eq(galleryImages.id, imageId),
        eq(galleryImages.galleryId, galleryId)
      ))
      .limit(1)

    if (!imageCheck[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Image not found in this gallery' })
    }

    // Get all captions for this image by joining with the global caption pool
    const imageCaptions = await db.select({
      captionId: captions.captionId,
      galleryImageId: galleryImageCaptions.galleryImageId,
      caption: captions.caption,
      createdById: galleryImageCaptions.createdById,
      createdAt: galleryImageCaptions.createdAt,
      isMain: galleryImageCaptions.isMain,
    })
      .from(galleryImageCaptions)
      .innerJoin(captions, eq(galleryImageCaptions.captionId, captions.captionId))
      .where(eq(galleryImageCaptions.galleryImageId, imageId))
      .orderBy(asc(galleryImageCaptions.isMain), asc(captions.captionId))

    return imageCaptions.map(c => ({
      captionId: c.captionId,
      galleryImageId: c.galleryImageId,
      caption: c.caption,
      createdById: c.createdById,
      createdAt: c.createdAt.toISOString(),
      isMain: c.isMain,
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-image-captions] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to fetch captions' })
  }
})
