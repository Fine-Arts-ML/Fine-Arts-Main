// Grant access to a guest for a gallery
import { db } from '~/lib/db'
import { galleryAccess, galleries } from '~/lib/gallery-schema'
import { userAccounts } from '~/lib/auth-schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot grant access' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    if (!galleryId || isNaN(galleryId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery ID' })
    }

    const body = await readBody(event)
    const { guestUserId, grantedById } = body

    if (!guestUserId || typeof guestUserId !== 'number') {
      throw createError({ statusCode: 400, statusMessage: 'guestUserId is required' })
    }

    // Check gallery ownership
    const galleryResult = await db.select()
      .from(galleries)
      .where(eq(galleries.id, galleryId))
      .limit(1)

    if (!galleryResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Gallery not found' })
    }

    if (user.role !== 'admin' && galleryResult[0].createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have permission to manage this gallery' })
    }

    // Check if guest exists and is actually a guest
    const guestResult = await db.select()
      .from(userAccounts)
      .where(eq(userAccounts.id, guestUserId))
      .limit(1)

    if (!guestResult[0]) {
      throw createError({ statusCode: 404, statusMessage: 'Guest user not found' })
    }

    if (guestResult[0].role !== 'guest') {
      throw createError({ statusCode: 400, statusMessage: 'User is not a guest' })
    }

    // Check if access already exists
    const existing = await db.select()
      .from(galleryAccess)
      .where(eq(galleryAccess.galleryId, galleryId))
      .andWhere(eq(galleryAccess.guestUserId, guestUserId))
      .limit(1)

    if (existing[0]) {
      throw createError({ statusCode: 409, statusMessage: 'Access already granted' })
    }

    // Grant access
    const grantedBy = grantedById || user.id
    const newAccess = await db.insert(galleryAccess)
      .values({
        galleryId,
        guestUserId,
        grantedById: grantedBy,
      })
      .returning()

    return {
      galleryId: newAccess[0].galleryId,
      guestUserId: newAccess[0].guestUserId,
      grantedById: newAccess[0].grantedById,
      grantedAt: newAccess[0].grantedAt.toISOString(),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[grant-gallery-access] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to grant access' })
  }
})
