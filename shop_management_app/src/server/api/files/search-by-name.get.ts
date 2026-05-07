/**
 * Search files by filename or display name.
 *
 * Query parameters:
 *   - query: Search term (required)
 *   - limit: Max results (default: 10)
 *   - previewSize: Preview dimension (default: 540)
 *
 * Reuses transformPreviewUrls from ~/server/utils/preview for preview URL conversion.
 */

import { transformPreviewUrls } from '~/server/utils/preview'

export default defineEventHandler(async (event) => {
  const query = getQuery(event).query as string
  const limit = parseInt(getQuery(event).limit as string || '10', 10)
  const previewSize = parseInt(getQuery(event).previewSize as string || '540', 10)

  if (!query || query.trim().length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'Query is required' })
  }

  const pg = await import('node_modules/@types/pg')
  const pool = new pg.Pool({
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'shop_management',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
  })

  try {
    const searchParam = `%${query.trim()}%`
    const rawQuery = `
      SELECT DISTINCT ON (ai.fileid)
        ai.fileid AS "fileId",
        ai.name AS "filename",
        ai.preview_url AS "previewUrl",
        dn.display_name AS "displayName"
      FROM bre_advance_index ai
      LEFT JOIN bre_display_name_index dni ON ai.fileid::text = dni.file_id
      LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
      WHERE ai.name ILIKE $1 OR dn.display_name ILIKE $1
      ORDER BY ai.fileid
      LIMIT $2
    `

    const result = await pool.query(rawQuery, [searchParam, limit])
    const rows = (result as any).rows

    return transformPreviewUrls(rows, previewSize)
  } finally {
    await pool.end()
  }
})
