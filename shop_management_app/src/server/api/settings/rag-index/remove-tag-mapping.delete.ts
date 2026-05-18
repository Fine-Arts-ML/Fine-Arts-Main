/**
 * Remove Tag-File Mapping API
 * Removes a single tag-file mapping from oc_systemtag_object_mapping.
 * This effectively "untags" a file without deleting the tag itself.
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { tag_id, file_id }: { tag_id: number; file_id: string } = body

  if (!tag_id || !file_id) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameters: tag_id and file_id',
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
    // Check if mapping exists
    const checkQuery = `
      SELECT COUNT(*) FROM oc_systemtag_object_mapping 
      WHERE systemtagid = $1 AND objectid::text = $2
    `
    const checkResult = await pool.query(checkQuery, [tag_id, file_id])
    
    if (parseInt(checkResult.rows[0].count) === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Tag-file mapping not found',
      })
    }

    // Delete the mapping
    const deleteQuery = `
      DELETE FROM oc_systemtag_object_mapping 
      WHERE systemtagid = $1 AND objectid::text = $2
    `
    await pool.query(deleteQuery, [tag_id, file_id])

    return {
      success: true,
      message: `Tag #${tag_id} removed from file ${file_id}`,
    }
  } catch (error: any) {
    console.error('[remove-tag-mapping] Error:', error)
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to remove tag mapping: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
