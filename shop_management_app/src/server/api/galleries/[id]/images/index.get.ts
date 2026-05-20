// Get all images in a gallery (ordered)
import { db } from '~/lib/db'
import { galleryImages, galleryAccess } from '~/lib/gallery-schema'
import { ocFilecache } from '~/lib/nextcloud-schema'
import { eq, and, asc } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
    }

    const galleryId = parseInt(getRouterParam(event, 'id') || '0', 10)
    if (!galleryId || isNaN(galleryId)) {
      throw createError({ statusCode: 400, statusMessage: 'Invalid gallery ID' })
    }

    // Check access for guests
    if (user.role === 'guest') {
      const accessCheck = await db.select()
        .from(galleryAccess)
        .where(and(
          eq(galleryAccess.galleryId, galleryId),
          eq(galleryAccess.guestUserId, user.id)
        ))
        .limit(1)
      
      if (!accessCheck[0]) {
        throw createError({ statusCode: 403, statusMessage: 'You do not have access to this gallery' })
      }
    }

    // Get images with file info from oc_filecache
    const images = await db.select({
      id: galleryImages.id,
      galleryId: galleryImages.galleryId,
      fileId: galleryImages.fileId,
      displayOrder: galleryImages.displayOrder,
      caption: galleryImages.caption,
      addedById: galleryImages.addedById,
      addedAt: galleryImages.addedAt,
      fileName: ocFilecache.name,
      path: ocFilecache.path,
    }).from(galleryImages)
      .leftJoin(ocFilecache, eq(galleryImages.fileId, ocFilecache.fileid))
      .where(eq(galleryImages.galleryId, galleryId))
      .orderBy(asc(galleryImages.displayOrder))

    return images.map(img => ({
      id: img.id,
      galleryId: img.galleryId,
      fileId: img.fileId,
      displayOrder: img.displayOrder,
      caption: img.caption,
      addedById: img.addedById,
      addedAt: img.addedAt.toISOString(),
      fileName: img.fileName,
      path: img.path,
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-gallery-images] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch gallery images',
    })
  }
})
