/**
 * Paginated endpoint to fetch all files for the "Browse All" view.
 *
 * Query parameters:
 *   - limit: Number of files per page (default: 48)
 *   - offset: Number of files to skip (default: 0)
 *   - sortBy: Sort field - 'fileid' or 'name' (default: 'fileid')
 *   - sortOrder: Sort order - 'asc' or 'desc' (default: 'asc')
 */

export default defineEventHandler(async (event) => {
  try {
    const limit = parseInt(getQuery(event).limit as string || '48', 10)
    const offset = parseInt(getQuery(event).offset as string || '0', 10)
    const sortBy = getQuery(event).sortBy as string || 'fileid'
    const sortOrder = (getQuery(event).sortOrder as string) || 'asc'

    // Validate sortBy against whitelist
    const validSortBy: string[] = ['fileid', 'name']
    if (!validSortBy.includes(sortBy)) {
      throw createError({
        statusCode: 400,
        statusMessage: `Invalid sortBy parameter. Must be one of: ${validSortBy.join(', ')}`,
      })
    }

    // Validate sortOrder against whitelist
    const validSortOrder: string[] = ['asc', 'desc']
    if (!validSortOrder.includes(sortOrder)) {
      throw createError({
        statusCode: 400,
        statusMessage: `Invalid sortOrder parameter. Must be one of: ${validSortOrder.join(', ')}`,
      })
    }

    // Determine ORDER BY clause based on sortBy
    // IMPORTANT: PostgreSQL requires DISTINCT ON expression to be first in ORDER BY
    // So we always start with ai.fileid, then add secondary sort for name
    let orderByClause: string
    if (sortBy === 'name') {
      // Primary sort by fileid (for DISTINCT ON), secondary sort by name (for user's sort preference)
      orderByClause = `ORDER BY ai.fileid ${sortOrder}, ai.name ${sortOrder}`
    } else {
      orderByClause = `ORDER BY ai.fileid ${sortOrder}`
    }

    const pg = await import('pg')
    const pool = new pg.Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    })

    try {
      const params = [limit, offset]
      const limitOffsetClause = `LIMIT $1 OFFSET $2`

      const result = await pool.query(
        `SELECT DISTINCT ON (ai.fileid)
          ai.fileid AS "fileId",
          ai.name AS "filename",
          ai.preview_url AS "previewUrl"
        FROM bre_advance_index ai
        ${orderByClause}
        ${limitOffsetClause}`,
        params
      )

      return (result as any).rows
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch files',
      data: error.message,
    })
  }
})
