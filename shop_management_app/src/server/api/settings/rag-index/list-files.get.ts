/**
 * List Files API
 * Queries Nextcloud's oc_filecache table directly to list files and directories
 * This works even when application tables are empty (at setup time)
 * Supports listing files from any user's home directory via storageNumericId
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const path = query.path as string
  const userId = query.userId as string
  const storageNumericId = query.storageNumericId as string | undefined

  if (!path) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: path',
    })
  }

  try {
    // Connect directly to Nextcloud database using environment variables
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
      // Get storage numeric_id - either from parameter or by userId
      let storageId: number
      if (storageNumericId && storageNumericId.trim() !== '') {
        storageId = parseInt(storageNumericId, 10)
        if (isNaN(storageId)) {
          throw createError({
            statusCode: 400,
            statusMessage: `Invalid storageNumericId: ${storageNumericId}`,
          })
        }
      } else if (userId && userId.trim() !== '') {
        // Fallback: look up by userId
        const storageResult = await pool.query(
          'SELECT numeric_id FROM oc_storages WHERE id = $1',
          [`home::${userId}`]
        )

        if (storageResult.rows.length === 0) {
          throw createError({
            statusCode: 404,
            statusMessage: `User home not found: home::${userId}`,
          })
        }

        storageId = parseInt(storageResult.rows[0].numeric_id, 10)
        if (isNaN(storageId)) {
          throw createError({
            statusCode: 500,
            statusMessage: `Invalid numeric_id for user: home::${userId}`,
          })
        }
      } else {
        throw createError({
          statusCode: 400,
          statusMessage: 'Missing required parameter: userId or storageNumericId',
        })
      }

      // Convert frontend path to Nextcloud internal path
      // Frontend sends paths like "/Tom" or "/Tom/Artwork"
      // Nextcloud stores paths like "files" or "files/Artwork"
      let internalPath: string
      if (path === '/' || path === `/${userId}`) {
        // Root of user's files → 'files'
        internalPath = 'files'
      } else if (path.startsWith(`/${userId}/`)) {
        // Subpath like "/Tom/Artwork" → "files/Artwork"
        const subPath = path.replace(`/${userId}/`, '')
        internalPath = `files/${subPath}`
      } else if (path.startsWith('/files')) {
        // Already in internal format
        internalPath = path.replace(/^\//, '')
      } else {
        // Fallback: use path as-is without leading slash
        internalPath = path.replace(/^\//, '')
      }

      // Build the full path prefix for parent lookup - ensure it ends with /
      const pathPrefix = internalPath ? `${internalPath}/` : ''

      // Get directories separately for cleaner output
      const directoriesResult = await pool.query(
        `SELECT
          fc.fileid,
          fc.name,
          'directory' AS type,
          0 AS size,
          fc.mtime,
          fc.etag
        FROM oc_filecache fc
        LEFT JOIN oc_mimetypes mt ON fc.mimetype = mt.id
        WHERE fc.storage = $1
          AND fc.parent IN (
            SELECT fileid FROM oc_filecache
            WHERE storage = $1 AND path = $2
          )
          AND mt.mimetype = 'httpd/unix-directory'
        ORDER BY fc.name ASC`,
        [storageId, internalPath]
      )

      const filesResult = await pool.query(
        `SELECT
          fc.fileid,
          fc.name,
          CASE
            WHEN mt.mimetype = 'httpd/unix-directory' THEN 'directory'
            ELSE 'file'
          END AS type,
          fc.size,
          fc.mtime,
          fc.etag,
          mt.mimetype AS mime_type,
          COALESCE(tag_status.tag_count, 0) as tag_count
        FROM oc_filecache fc
        LEFT JOIN oc_mimetypes mt ON fc.mimetype = mt.id
        LEFT JOIN LATERAL (
          SELECT COUNT(*) as tag_count
          FROM oc_systemtag_object_mapping som
          WHERE som.objectid::text = fc.fileid::text
            AND som.objecttype = 'files'
        ) tag_status ON true
        WHERE fc.storage = $1
          AND fc.parent IN (
            SELECT fileid FROM oc_filecache
            WHERE storage = $1 AND path = $2
          )
          AND mt.mimetype != 'httpd/unix-directory'
        ORDER BY fc.name ASC`,
        [storageId, internalPath]
      )

      const directories = directoriesResult.rows.map((row: any) => ({
        fileid: parseInt(row.fileid),
        name: row.name,
        type: row.type as 'directory',
        size: 0,
        mtime: parseInt(row.mtime) * 1000, // Convert to milliseconds
        etag: row.etag,
      }))

      const files = filesResult.rows.map((row: any) => ({
        fileid: parseInt(row.fileid),
        name: row.name,
        type: row.type as 'file',
        size: parseInt(row.size),
        mtime: parseInt(row.mtime) * 1000, // Convert to milliseconds
        etag: row.etag,
        mimeType: row.mime_type,
        tagCount: parseInt(row.tag_count) || 0,
      }))

      return {
        path,
        directories,
        files,
        storageId,
      }
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    console.error('Error listing files:', error)
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to list files',
      data: error.data,
    })
  }
})
