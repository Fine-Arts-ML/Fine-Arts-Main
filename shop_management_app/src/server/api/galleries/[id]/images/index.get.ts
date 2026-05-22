// Get all images in a gallery (ordered)
import { db } from '~/lib/db'
import { galleryImages, galleryAccess } from '~/lib/gallery-schema'
import { ocFilecache } from '~/lib/nextcloud-schema'
import { eq, and, asc } from 'drizzle-orm'
import { Pool } from 'pg'

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

    // Build result array
    const result = images.map(img => ({
      id: img.id,
      galleryId: img.galleryId,
      fileId: img.fileId,
      displayOrder: img.displayOrder,
      caption: img.caption,
      addedById: img.addedById,
      addedAt: img.addedAt.toISOString(),
      fileName: img.fileName,
      path: img.path,
      description: null as string | null,
    }))

    // Hybrid approach: Fetch descriptions for all files in this gallery in a single query
    if (result.length > 0) {
      const dbHost = process.env.DB_HOST || 'localhost'
      const dbPort = Number(process.env.DB_PORT) || 5432
      const dbName = process.env.DB_NAME || 'nextpsql'
      const dbUser = process.env.DB_USER || 'nextuser'
      const dbPassword = process.env.DB_PASSWORD || ''

      const pool = new Pool({
        host: dbHost,
        port: dbPort,
        database: dbName,
        user: dbUser,
        password: dbPassword,
      })

      try {
        // Build parameter placeholder string: $1, $2, $3, ...
        const placeholders = result.map((_, i) => `$${i + 1}`).join(', ')
        
        // Fetch descriptions for all files in this gallery in one query
        const descResult = await pool.query(
          `SELECT d.file_id, d.description
           FROM bre_descriptions d
           WHERE d.file_id IN (${placeholders})
           ORDER BY d.file_id, d.pinned DESC, d.created_at DESC`,
          result.map(img => img.fileId.toString())
        )

        // Create a map of fileId -> description (only pinned first, then latest)
        const descriptionMap = new Map<string, string>()
        for (const row of descResult.rows) {
          const fileId = row.file_id
          if (!descriptionMap.has(fileId)) {
            descriptionMap.set(fileId, row.description)
          }
        }

        // Attach descriptions to result
        for (const img of result) {
          img.description = descriptionMap.get(img.fileId.toString()) || null
        }
      } catch (descError: any) {
        console.error('[get-gallery-images] Warning: Failed to fetch descriptions:', descError.message)
        // Continue without descriptions - non-critical
      } finally {
        await pool.end()
      }
    }

    return result
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[get-gallery-images] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch gallery images',
    })
  }
})
