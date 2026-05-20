// Update gallery
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

    // Only admins and users can update galleries
    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot update galleries' })
    }

    const id = getRouterParam(event, 'id')
    if (!id) {
      throw createError({ statusCode: 400, statusMessage: 'Gallery ID is required' })
    }

    const galleryId = parseInt(id, 10)

    // Get gallery to check ownership
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    const gallery = galleryResult[0]

    // Check permissions (admin can update any, users can only update their own)
    if (user.role !== 'admin' && gallery.createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to update this gallery' })
    }

    const body = await readBody(event)
    const { name, description, isActive } = body

    const updateData: Record<string, any> = {
      updatedById: user.id,
    }

    if (name !== undefined) {
      if (typeof name !== 'string' || name.trim().length === 0) {
        throw createError({ statusCode: 400, statusMessage: 'Gallery name cannot be empty' })
      }
      updateData.name = name.trim()
    }

    if (description !== undefined) {
      updateData.description = description || null
    }

    if (isActive !== undefined) {
      updateData.isActive = Boolean(isActive)
    }

    const updatedGallery = await db.update(galleries)
      .set(updateData)
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
    console.error('[update-gallery] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update gallery',
    })
  }
})
