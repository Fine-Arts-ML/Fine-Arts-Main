// PUT /api/galleries/[id]/images/[imageId]/captions/bulk
// Replaces all caption links for a gallery-image pair

import { db } from '~/lib/db'
import { galleryImageCaptions, captions, galleryImages, galleries } from '~/lib/gallery-schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot modify captions' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)

    if (!galleryId || !imageId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or image ID' })
    }

    const body = await readBody(event)
    const { captionAssignments } = body

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

    // Verify the image belongs to this gallery
    const imageCheck = await db.select()
      .from(galleryImages)
      .where(and(
        eq(galleryImages.id, imageId),
        eq(galleryImages.galleryId, galleryId)
      ))
      .limit(1)

    if (!imageCheck[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Image not found in gallery' })
    }

    // Delete existing caption links for this image
    await db.delete(galleryImageCaptions)
      .where(eq(galleryImageCaptions.galleryImageId, imageId))

    // Insert new caption links (empty array = no captions, allowed)
    if (Array.isArray(captionAssignments) && captionAssignments.length > 0) {
      const newLinks = captionAssignments.map(a => ({
        galleryImageId: imageId,
        captionId: a.captionId,
        isMain: a.isMain ?? false,
        createdById: user.id,
      }))

      await db.insert(galleryImageCaptions).values(newLinks)
    }

    // Return updated captions
    const updated = await db.select({
      id: galleryImageCaptions.id,
      galleryImageId: galleryImageCaptions.galleryImageId,
      captionId: galleryImageCaptions.captionId,
      caption: captions.caption,
      isMain: galleryImageCaptions.isMain,
      createdById: galleryImageCaptions.createdById,
      createdAt: galleryImageCaptions.createdAt,
    })
      .from(galleryImageCaptions)
      .leftJoin(captions, eq(galleryImageCaptions.captionId, captions.captionId))
      .where(eq(galleryImageCaptions.galleryImageId, imageId))

    return updated.map(u => ({
      id: u.id,
      galleryImageId: u.galleryImageId,
      captionId: u.captionId,
      caption: u.caption || '',
      isMain: u.isMain,
      createdById: u.createdById,
      createdAt: u.createdAt.toISOString(),
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[bulk-caption-update] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to update captions' })
  }
})
