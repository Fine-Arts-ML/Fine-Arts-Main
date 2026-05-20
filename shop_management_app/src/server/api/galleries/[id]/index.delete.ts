// Delete gallery (cascades to images and access)
import { db } from '~/lib/db'
import { galleries } from '~/lib/gallery-schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    // Only admins can delete galleries
    if (user.role !== 'admin') {
      throw createError({ statusCode: 403, statusMessage: 'Only admins can delete galleries' })
    }

    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({ statusCode: 400, statusMessage: 'Gallery ID is required' })
    }

    const galleryId = parseInt(id, 10)

    // Check if gallery exists
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    // Delete gallery (cascade will handle gallery_images and gallery_access)
    await db.delete(galleries)
      .where(eq(galleries.id, galleryId))

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[delete-gallery] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to delete gallery',
    })
  }
})
