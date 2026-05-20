// Get gallery details with images and access list
import { db } from '~/lib/db'
import { galleries, galleryImages, galleryAccess } from '~/lib/gallery-schema'
import { ocFilecache } from '~/lib/nextcloud-schema'
import { eq, and, asc } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    // Check authentication
    const user = event.context.user
    if (!user) {
      throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
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

    // Check access
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
    } else if (user.role !== 'admin' && gallery.createdById !== user.id) {
      throw createError({ statusCode: 403, statusMessage: 'You do not have access to this gallery' })
    }

    // Get images with file info from oc_filecache
    const imagesWithFiles = await db.select({
      id: galleryImages.id,
      galleryId: galleryImages.galleryId,
      fileId: galleryImages.fileId,
      displayOrder: galleryImages.displayOrder,
      caption: galleryImages.caption,
      addedById: galleryImages.addedById,
      addedAt: galleryImages.addedAt,
      fileName: ocFilecache.name,
      path: ocFilecache.path,
      previewUrl: ocFilecache.path,
    }).from(galleryImages)
      .leftJoin(ocFilecache, eq(galleryImages.fileId, ocFilecache.fileid))
      .where(eq(galleryImages.galleryId, galleryId))
      .orderBy(asc(galleryImages.displayOrder))

    // Get access list with guest info
    const { userAccounts } = await import('~/lib/auth-schema')
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

    return {
      id: gallery.id,
      name: gallery.name,
      description: gallery.description,
      createdById: gallery.createdById,
      updatedById: gallery.updatedById,
      isActive: gallery.isActive,
      createdAt: gallery.createdAt.toISOString(),
      updatedAt: gallery.updatedAt.toISOString(),
      images: imagesWithFiles.map(img => ({
        id: img.id,
        galleryId: img.galleryId,
        fileId: img.fileId,
        displayOrder: img.displayOrder,
        caption: img.caption,
        addedById: img.addedById,
        addedAt: img.addedAt.toISOString(),
        fileName: img.fileName,
        path: img.path,
        previewUrl: img.path,
      })),
      access: accessList.map(a => ({
        galleryId: a.galleryId,
        guestUserId: a.guestUserId,
        grantedById: a.grantedById,
        grantedAt: a.grantedAt.toISOString(),
        guestName: a.guestName,
        guestDisplayname: a.guestDisplayname,
      })),
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-gallery] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch gallery',
    })
  }
})
