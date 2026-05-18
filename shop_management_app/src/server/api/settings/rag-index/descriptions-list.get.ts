/**
 * Descriptions List API
 * Returns paginated list of all descriptions with file info.
 * Used by the Descriptions tab in the sync page.
 */

import { Pool } from 'pg'

interface DescriptionEntry {
  id: number
  description: string
  pinned: boolean
  createdAt: string
}

interface DescriptionItem {
  file_id: string
  file_name: string
  preview_url: string
  descriptions: DescriptionEntry[]
}

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const search = (query.search as string) || ''
  const filter = (query.filter as string) || 'all'
  const limit = Math.min(parseInt(query.limit as string) || 50, 200)
  const offset = parseInt(query.offset as string) || 0

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
    // Build WHERE clause dynamically
    // Tags and descriptions are independent systems — no tag mapping JOIN needed
    const whereConditions: string[] = []
    const params: any[] = []
    let paramIndex = 1

    if (search) {
      whereConditions.push('(fc.name ILIKE $' + paramIndex + ' OR EXISTS (SELECT 1 FROM bre_descriptions d2 WHERE d2.file_id = fc.fileid::text AND d2.description ILIKE $' + paramIndex + '))')
      params.push('%' + search + '%')
      paramIndex++
    }

    const whereClause = whereConditions.length > 0 ? 'WHERE ' + whereConditions.join(' AND ') : ''

    // Get total count of distinct files with descriptions (no tag mapping JOIN)
    const countQuery = `
      SELECT COUNT(DISTINCT d.file_id)::int AS count
      FROM bre_descriptions d
      JOIN oc_filecache fc ON d.file_id = fc.fileid::text
      ${whereClause}
    `
    const countResult = await pool.query(countQuery, params)
    const total = parseInt(countResult.rows[0].count)

    // Get paginated files with their descriptions aggregated into an array
    // GROUP BY groups all descriptions for the same file into one row
    const descQuery = `
      SELECT
        d.file_id,
        fc.name AS file_name,
        json_agg(
          json_build_object(
            'id', d.id,
            'description', d.description,
            'pinned', d.pinned,
            'createdAt', TO_CHAR(d.created_at, 'YYYY-MM-DD"T"HH24:MI:SS')
          )
          ORDER BY d.pinned DESC, d.created_at DESC
        ) AS descriptions
      FROM bre_descriptions d
      JOIN oc_filecache fc ON d.file_id = fc.fileid::text
      ${whereClause}
      GROUP BY d.file_id, fc.name
      ORDER BY MAX(d.created_at) DESC
      LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
    `
    const descResult = await pool.query(descQuery, [...params, limit, offset])
    
    const descriptions: DescriptionItem[] = descResult.rows.map(row => ({
      file_id: row.file_id,
      file_name: row.file_name || 'Unknown',
      preview_url: '', // Set by frontend using NEXTCLOUD_URL
      descriptions: row.descriptions || [],
    }))

    return {
      descriptions,
      total,
      limit,
      offset,
    }
  } catch (error: any) {
    console.error('[descriptions-list] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch descriptions: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
