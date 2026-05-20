// Add image(s) to gallery
import { db } from '~/lib/db'
import { galleryImages, galleries } from '~/lib/gallery-schema'
import { ocFilecache } from '~/lib/nextcloud-schema'
import { eq, and, max as drizzleMax } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot add images to galleries' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    if (!galleryId || isNaN(galleryId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery ID' })
    }

    const body = await readBody(event)
    const { fileIds, caption } = body

    if (!Array.isArray(fileIds) || fileIds.length === 0) {
      throw createError({ statusCode: 400, statusMessage: 'fileIds array is required and cannot be empty' })
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

    // Get max display order for this gallery
    const maxOrderResult = await db.select({ 
      max: drizzleMax(galleryImages.displayOrder) 
    })
      .from(galleryImages)
      .where(eq(galleryImages.galleryId, galleryId))

    const maxOrder = maxOrderResult[0]?.max || 0

    // Insert images with sequential order
    const newImages = []
    for (let i = 0; i < fileIds.length; i++) {
      const fileId = fileIds[i]
      if (!fileId || (typeof fileId !== 'number' && typeof fileId !== 'bigint')) {
        continue
      }

      // Convert string IDs to numbers (accept both for robustness)
      const fileIdNum = typeof fileId === 'string' ? parseInt(fileId, 10) : Number(fileId)
      if (isNaN(fileIdNum)) {
        console.warn('[add-gallery-images] Skipping invalid fileId:', fileId)
        continue
      }

      // Check if image already exists in gallery
      const existing = await db.select()
        .from(galleryImages)
        .where(and(
          eq(galleryImages.galleryId, galleryId),
          eq(galleryImages.fileId, fileIdNum)
        ))
        .limit(1)

      if (existing[0]) continue // Skip duplicates

      const newImage = await db.insert(galleryImages)
        .values({
          galleryId,
          fileId: fileIdNum,
          displayOrder: maxOrder + i + 1,
          caption: caption || null,
          addedById: user.id,
        })
        .returning()

      if (newImage[0]) {
        newImages.push(newImage[0])
      }
    }

    return newImages.map(img => ({
      id: img.id,
      galleryId: img.galleryId,
      fileId: img.fileId,
      displayOrder: img.displayOrder,
      caption: img.caption,
      addedById: img.addedById,
      addedAt: img.addedAt.toISOString(),
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[add-gallery-images] Error:', error)
    
    // Handle duplicate key constraint violation (image already in gallery)
    if (error.code === '23505') { // PostgreSQL unique violation
      throw createError({
        statusCode: 409,
        statusMessage: 'One or more images are already in this gallery',
      })
    }
    
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to add images to gallery',
    })
  }
})
