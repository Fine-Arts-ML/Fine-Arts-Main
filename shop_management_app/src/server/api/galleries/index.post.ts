// Create a new gallery
import { db } from '~/lib/db'
import { galleries } from '~/lib/gallery-schema'
import { userAccounts } from '~/lib/auth-schema'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    // Only admins and users can create galleries
    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot create galleries' })
    }

    const body = await readBody(event)
    const { name, description } = body

    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Gallery name is required',
      })
    }

    const newGallery = await db.insert(galleries)
      .values({
        name: name.trim(),
        description: description || null,
        createdById: user.id,
      })
      .returning()

    return {
      id: newGallery[0].id,
      name: newGallery[0].name,
      description: newGallery[0].description,
      createdById: newGallery[0].createdById,
      updatedById: newGallery[0].updatedById,
      isActive: newGallery[0].isActive,
      createdAt: newGallery[0].createdAt.toISOString(),
      updatedAt: newGallery[0].updatedAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[create-gallery] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to create gallery',
    })
  }
})
