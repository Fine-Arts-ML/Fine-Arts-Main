// POST /api/galleries/[id]/images/[imageId]/captions
// Creates a caption in the global caption pool and links it to a gallery image

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
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot add captions' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    const imageId = parseInt(getRouterParam(event, 'imageId') || '0', 10)

    if (!galleryId || !imageId) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery or image ID' })
    }

    const body = await readBody(event)
    const { caption: captionText } = body

    if (!captionText || typeof captionText !== 'string' || captionText.trim() === '') {
      throw createError({ statusCode: 400, statusMessage: 'Caption text is required' })
    }

    const trimmedCaption = captionText.trim()

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
      throw createError({ statusCode: 404, statusMessage: 'Image not found in this gallery' })
    }

    // Check if caption already exists in the global pool (case-insensitive)
    let captionId: number
    const existingCaption = await db.select()
      .from(captions)
      .where(sql`LOWER(caption) = ${trimmedCaption.toLowerCase()}`)
      .limit(1)

    if (existingCaption.length > 0) {
      captionId = existingCaption[0].captionId
    } else {
      // Create new caption in the global pool
      const newCaption = await db.insert(captions)
        .values({
          caption: trimmedCaption,
          createdById: user.id,
        })
        .returning({ captionId: captions.captionId })
      
      if (!newCaption[0]) {
        throw createError({ statusCode: 500, statusMessage: 'Failed to create caption' })
      }
      captionId = newCaption[0].captionId
    }

    // Check if this link already exists
    const existingLink = await db.select()
      .from(galleryImageCaptions)
      .where(and(
        eq(galleryImageCaptions.galleryImageId, imageId),
        eq(galleryImageCaptions.captionId, captionId)
      ))
      .limit(1)

    if (existingLink[0]) {
      throw createError({ statusCode: 409, statusMessage: 'This caption is already linked to this image' })
    }

    // Create the caption link
    const newLink = await db.insert(galleryImageCaptions)
      .values({
        galleryImageId: imageId,
        captionId: captionId,
        isMain: false,
        createdById: user.id,
      })
      .returning({
        id: galleryImageCaptions.id,
        galleryImageId: galleryImageCaptions.galleryImageId,
        captionId: galleryImageCaptions.captionId,
        isMain: galleryImageCaptions.isMain,
        createdById: galleryImageCaptions.createdById,
        createdAt: galleryImageCaptions.createdAt,
      })

    // Fetch the actual caption text from the pool
    const captionData = await db.select({
      caption: captions.caption,
    })
      .from(captions)
      .where(eq(captions.captionId, captionId))
      .limit(1)

    if (!captionData[0]) {
      throw createError({ statusCode: 500, statusMessage: 'Failed to retrieve caption data' })
    }

    return {
      id: newLink[0].id,
      captionId: newLink[0].captionId,
      galleryImageId: newLink[0].galleryImageId,
      caption: captionData[0].caption,
      isMain: newLink[0].isMain,
      createdById: newLink[0].createdById,
      createdAt: newLink[0].createdAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[add-image-caption] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to add caption' })
  }
})
