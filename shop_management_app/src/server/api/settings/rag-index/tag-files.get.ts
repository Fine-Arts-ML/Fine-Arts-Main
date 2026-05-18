/**
 * Tag Files API
 * Returns paginated list of files associated with a specific tag.
 * Replaces the need to transfer all tagFileMappings in graph-data response.
 */

import { Pool } from 'pg'

interface TagFileResult {
  file_id: string
  file_name: string
  has_description: boolean
}

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const tagId = query.tag_id as string
  const limit = Math.min(parseInt(query.limit as string) || 50, 200)
  const offset = parseInt(query.offset as string) || 0

  if (!tagId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: tag_id',
    })
  }

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
    // Get total count
    const countQuery = `
      SELECT COUNT(DISTINCT m.objectid::text)::int AS count
      FROM oc_systemtag_object_mapping m
      WHERE m.systemtagid = $1
    `
    const countResult = await pool.query(countQuery, [tagId])
    const total = parseInt(countResult.rows[0].count)

    // Get paginated files with description status
    const filesQuery = `
      SELECT 
        m.objectid::text AS file_id,
        fc.name AS file_name,
        CASE WHEN d.file_id IS NOT NULL THEN true ELSE false END AS has_description
      FROM oc_systemtag_object_mapping m
      LEFT JOIN oc_filecache fc ON m.objectid::text = fc.fileid::text
        AND fc.name NOT LIKE '.%' AND fc.mimetype IN (
          SELECT id FROM oc_mimetypes WHERE mimetype LIKE 'image/%'
        )
      LEFT JOIN bre_descriptions d ON m.objectid::text = d.file_id
      WHERE m.systemtagid = $1
      ORDER BY fc.name
      LIMIT $2 OFFSET $3
    `
    const filesResult = await pool.query(filesQuery, [tagId, limit, offset])
    
    const files: TagFileResult[] = filesResult.rows.map(row => ({
      file_id: row.file_id,
      file_name: row.file_name || 'Unknown',
      has_description: row.has_description,
    }))

    return {
      files,
      total,
      limit,
      offset,
    }
  } catch (error: any) {
    console.error('[tag-files] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch tag files: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
