/**
 * File Descriptions API
 * Returns all descriptions for a specific file.
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
        id,
        description,
        created_at,
        updated_at,
        pinned
      FROM bre_descriptions
      WHERE file_id = $1
      ORDER BY pinned DESC, created_at DESC
    `
    const result = await pool.query(queryStr, [fileId])

    return {
      descriptions: result.rows.map(row => ({
        id: parseInt(row.id),
        description: row.description,
        createdAt: row.created_at,
        updatedAt: row.updated_at,
        pinned: row.pinned,
      })),
    }
  } catch (error: any) {
    console.error('[file-descriptions] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch file descriptions: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
