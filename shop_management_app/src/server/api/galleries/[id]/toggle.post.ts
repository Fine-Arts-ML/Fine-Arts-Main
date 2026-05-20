// Toggle gallery active/inactive status
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

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot toggle galleries' })
    }

    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({ statusCode: 400, statusMessage: 'Gallery ID is required' })
    }

    const galleryId = parseInt(id, 10)

    // Get gallery
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    const gallery = galleryResult[0]

    // Check permissions
    if (user.role !== 'admin' && gallery.createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to toggle this gallery' })
    }

    // Toggle and update
    const updatedGallery = await db.update(galleries)
      .set({ 
        isActive: !gallery.isActive,
        updatedById: user.id,
      })
      .where(eq(galleries.id, galleryId))
      .returning()

    return {
      id: updatedGallery[0].id,
      name: updatedGallery[0].name,
      description: updatedGallery[0].description,
      createdById: updatedGallery[0].createdById,
      updatedById: updatedGallery[0].updatedById,
      isActive: updatedGallery[0].isActive,
      createdAt: updatedGallery[0].createdAt.toISOString(),
      updatedAt: updatedGallery[0].updatedAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[toggle-gallery] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to toggle gallery',
    })
  }
})
