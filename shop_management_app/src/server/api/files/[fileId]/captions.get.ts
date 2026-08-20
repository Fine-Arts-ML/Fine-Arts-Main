// GET /api/files/[fileId]/captions
// Returns all captions already associated with the same file (from galleries and shops)

import { eq, desc, sql } from 'drizzle-orm'
import { defineEventHandler, getRouterParams } from 'h3'
import { db } from '~/lib/db'
import { galleryImages, galleries, galleryImageCaptions, captions } from '~/lib/gallery-schema'

export default defineEventHandler(async (event) => {
  const user = event.context.user
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const { fileId } = getRouterParams(event)
  if (!fileId) {
    throw createError({ statusCode: 400, statusMessage: 'File ID is required' })
  }

  const fileIdStr = fileId // bre_display_name_index uses string file_id

  // Get shop display names for this file
  const shopDisplayNamesResult: any = await db.execute(
    sql`SELECT ddi.shop_id, dn.display_name, ddi.display_name_id
        FROM bre_display_name_index ddi
        JOIN bre_display_names dn ON ddi.display_name_id = dn.display_name_id
        WHERE ddi.file_id = ${fileIdStr}`
  )
  const shopDisplayNames: any[] = shopDisplayNamesResult?.rows || []

  // Group by shop
  const shopsByShop: Record<number, { shopId: number; shopName: string; captions: Array<{ captionId: number; caption: string; createdById: number; createdAt: string }> }> = {}
  
  for (const row of shopDisplayNames) {
    const shopId = parseInt(row.shop_id, 10)
    const displayName = row.display_name
    const displayNameId = parseInt(row.display_name_id, 10)
    
    if (!shopsByShop[shopId]) {
      // Get shop name first time we encounter this shop
      const shopResult: any[] = await db.execute(
        sql`SELECT shop_name FROM bre_shops WHERE shop_id = ${shopId} LIMIT 1`
      )
      const shopName = shopResult[0]?.shop_name || `Shop ${shopId}`
      shopsByShop[shopId] = { shopId, shopName, captions: [] }
    }
    
    shopsByShop[shopId].captions.push({
      captionId: -displayNameId, // Negative temp ID
      caption: displayName,
      createdById: 0,
      createdAt: new Date().toISOString(),
    })
  }

  const shops = Object.values(shopsByShop)

  // Get captions from gallery-image-captions for this file
  const galleryCaptions = await db.select({
    galleryId: galleries.id,
    galleryName: galleries.name,
    galleryImageId: galleryImages.id,
    captionId: captions.captionId,
    caption: captions.caption,
    isMain: galleryImageCaptions.isMain,
    createdById: galleryImageCaptions.createdById,
    createdAt: galleryImageCaptions.createdAt,
  })
    .from(galleryImageCaptions)
    .innerJoin(galleryImages, eq(galleryImageCaptions.galleryImageId, galleryImages.id))
    .innerJoin(galleries, eq(galleryImages.galleryId, galleries.id))
    .innerJoin(captions, eq(galleryImageCaptions.captionId, captions.captionId))
    .where(eq(galleryImages.fileId, parseInt(fileId, 10)))

  // Group by gallery
  const galleriesGrouped: Record<string, any[]> = {}
  for (const cap of galleryCaptions) {
    const key = String(cap.galleryId)
    if (!galleriesGrouped[key]) {
      galleriesGrouped[key] = []
    }
    galleriesGrouped[key].push({
      captionId: cap.captionId,
      caption: cap.caption,
      isMain: cap.isMain,
      createdById: cap.createdById,
      createdAt: cap.createdAt,
    })
  }

  return {
    galleries: Object.entries(galleriesGrouped).map(([galleryId, caps]) => ({
      galleryId: parseInt(galleryId),
      galleryName: caps[0].galleryName,
      galleryImageId: caps[0].galleryImageId,
      captions: caps.map(c => ({
        captionId: c.captionId,
        caption: c.caption,
        isMain: c.isMain,
        createdById: c.createdById,
        createdAt: c.createdAt.toISOString(),
      })),
    })),
    shops,
  }
})
