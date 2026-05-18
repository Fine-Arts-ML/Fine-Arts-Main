/**
 * File Tags API
 * Returns all tags associated with a specific file.
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const fileId = query.file_id as string

  if (!fileId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: file_id',
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
    const queryStr = `
      SELECT 
        s.id,
        s.name
      FROM oc_systemtag s
      JOIN oc_systemtag_object_mapping m ON s.id = m.systemtagid
      WHERE m.objectid::text = $1
      ORDER BY s.name
    `
    const result = await pool.query(queryStr, [fileId])

    // Get file name
    const fileQuery = `
      SELECT name FROM oc_filecache WHERE fileid::text = $1
    `
    const fileResult = await pool.query(fileQuery, [fileId])
    const fileName = fileResult.rows.length > 0 ? fileResult.rows[0].name : 'Unknown'

    return {
      fileName,
      tags: result.rows.map(row => ({
        id: parseInt(row.id),
        name: row.name,
      })),
    }
  } catch (error: any) {
    console.error('[file-tags] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch file tags: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
