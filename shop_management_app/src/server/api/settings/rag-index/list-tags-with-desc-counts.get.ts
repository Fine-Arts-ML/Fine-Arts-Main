/**
 * List Tags with Description Counts API
 * Returns all tags with file counts and description counts for the list view.
 */

import { Pool } from 'pg'

interface TagWithDescCounts {
  id: number
  name: string
  num_files: number
  files_with_descriptions: number
}

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const search = (query.search as string) || ''
  const filterDesc = (query.filter_desc as string) || '' // 'has' | 'none'
  const sortBy = (query.sort_by as string) || 'name'
  const sortOrder = (query.sort_order as string) || 'asc'
  const limit = Math.min(parseInt(query.limit as string) || 100, 500)
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
    const whereConditions: string[] = []
    const params: any[] = []
    let paramIndex = 1

    if (search) {
      whereConditions.push(`s.name ILIKE $${paramIndex}`)
      params.push(`%${search}%`)
      paramIndex++
    }

    const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : ''

    // Get total count first
    const countQuery = `
      SELECT COUNT(DISTINCT s.id)
      FROM oc_systemtag s
      LEFT JOIN oc_systemtag_object_mapping m ON s.id = m.systemtagid
      ${whereClause}
    `
    const countResult = await pool.query(countQuery, params)
    const total = parseInt(countResult.rows[0].count)

    // Build base query
    let tagsQuery = `
      SELECT 
        s.id,
        s.name,
        COUNT(DISTINCT m.objectid::text)::int AS num_files,
        COUNT(DISTINCT CASE WHEN d.file_id IS NOT NULL THEN m.objectid::text END)::int AS files_with_descriptions
      FROM oc_systemtag s
      LEFT JOIN oc_systemtag_object_mapping m ON s.id = m.systemtagid
      LEFT JOIN bre_descriptions d ON m.objectid::text = d.file_id
      ${whereClause}
      GROUP BY s.id, s.name
      HAVING COUNT(DISTINCT m.objectid::text) >= 1
    `

    // Add ordering
    if (sortBy === 'name') {
      tagsQuery += ` ORDER BY s.name ${sortOrder === 'desc' ? 'DESC' : 'ASC'}`
    } else if (sortBy === 'num_files') {
      tagsQuery += ` ORDER BY num_files ${sortOrder === 'desc' ? 'DESC' : 'ASC'}`
    }

    // Add pagination
    tagsQuery += ` LIMIT $${paramIndex}`
    params.push(limit)
    paramIndex++
    tagsQuery += ` OFFSET $${paramIndex}`
    params.push(offset)
    paramIndex++

    const result = await pool.query(tagsQuery, params)
    
    let tags: TagWithDescCounts[] = result.rows.map(row => ({
      id: parseInt(row.id),
      name: row.name,
      num_files: parseInt(row.num_files),
      files_with_descriptions: parseInt(row.files_with_descriptions),
    }))

    // Apply description filter if needed (can't do in SQL with HAVING easily)
    if (filterDesc === 'has') {
      tags = tags.filter(t => t.files_with_descriptions > 0)
    } else if (filterDesc === 'none') {
      tags = tags.filter(t => t.files_with_descriptions === 0)
    }

    return {
      tags,
      total,
      limit,
      offset,
    }
  } catch (error: any) {
    console.error('[list-tags-with-desc-counts] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch tags: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
