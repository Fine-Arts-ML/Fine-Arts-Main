// PUT /api/galleries/[id]/images/[imageId]/captions/[captionId]
// Updates a caption in the global caption pool and optionally toggles isMain

import { db } from '~/lib/db'
import { galleryImageCaptions, galleryImages, galleries, captions } from '~/lib/gallery-schema'
import { eq, and, sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot update captions' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)
    const captionId = parseInt(getRouterParam(event, 'captionId') || '0', 10)

    if (!galleryId || !imageId || !captionId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery, image, or caption ID' })
    }

    const body = await readBody(event)
    const { caption, isMain } = body

    if (!caption || typeof caption !== 'string' || caption.trim() === '') {
      throw createError({ statusCode: 400, statusMessage: 'Caption text is required' })
    }

    const trimmedCaption = caption.trim()

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

    // Update the caption in the global pool
    await db.update(captions)
      .set({ caption: trimmedCaption })
      .where(eq(captions.captionId, captionId))

    // Update isMain if provided
    if (isMain !== undefined) {
      await db.update(galleryImageCaptions)
        .set({ isMain: isMain })
        .where(and(
          eq(galleryImageCaptions.captionId, captionId),
          eq(galleryImageCaptions.galleryImageId, imageId)
        ))
    }

    // Fetch updated caption data
    const updatedCaption = await db.select({
      captionId: captions.captionId,
      caption: captions.caption,
      createdById: captions.createdById,
      createdAt: captions.createdAt,
    })
      .from(captions)
      .where(eq(captions.captionId, captionId))
      .limit(1)

    const linkData = await db.select({
      isMain: galleryImageCaptions.isMain,
      galleryImageId: galleryImageCaptions.galleryImageId,
      createdAt: galleryImageCaptions.createdAt,
    })
      .from(galleryImageCaptions)
      .where(and(
        eq(galleryImageCaptions.captionId, captionId),
        eq(galleryImageCaptions.galleryImageId, imageId)
      ))
      .limit(1)

    if (!updatedCaption[0] || !linkData[0]) {
      throw createError({ statusCode: 500, statusMessage: 'Failed to retrieve updated caption' })
    }

    return {
      captionId: updatedCaption[0].captionId,
      galleryImageId: linkData[0].galleryImageId,
      caption: updatedCaption[0].caption,
      isMain: linkData[0].isMain,
      createdById: updatedCaption[0].createdById,
      createdAt: linkData[0].createdAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[update-caption] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to update caption' })
  }
})
