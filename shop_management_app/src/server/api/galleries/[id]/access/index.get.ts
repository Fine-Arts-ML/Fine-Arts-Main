// Get list of guests with access to a gallery
import { db } from '~/lib/db'
import { galleryAccess, galleryImages, galleries } from '~/lib/gallery-schema'
import { userAccounts } from '~/lib/auth-schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    if (!galleryId || isNaN(galleryId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery ID' })
    }

    // Check access - user must own gallery or be admin to view access list
    if (user.role === 'guest') {
      throw createError({ statusCode: 403, statusMessage: 'Guests cannot view access lists' })
    }

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

    // Get access list with guest info
    const accessList = await db.select({
      galleryId: galleryAccess.galleryId,
      guestUserId: galleryAccess.guestUserId,
      grantedById: galleryAccess.grantedById,
      grantedAt: galleryAccess.grantedAt,
      guestName: userAccounts.nextcloudUid,
      guestDisplayname: userAccounts.role,
    }).from(galleryAccess)
      .leftJoin(userAccounts, eq(galleryAccess.guestUserId, userAccounts.id))
      .where(eq(galleryAccess.galleryId, galleryId))

    return accessList.map(a => ({
      galleryId: a.galleryId,
      guestUserId: a.guestUserId,
      grantedById: a.grantedById,
      grantedAt: a.grantedAt.toISOString(),
      guestName: a.guestName,
      guestDisplayname: a.guestDisplayname,
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-gallery-access] Error:', error)
    throw createError({ statusCode: 500, statusMessage: 'Failed to fetch access list' })
  }
})
