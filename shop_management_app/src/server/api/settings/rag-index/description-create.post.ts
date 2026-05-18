/**
 * Create Description API
 * Creates a new description in bre_descriptions for a file.
 * Enforces: max 3 descriptions per file (oldest non-pinned removed if limit exceeded).
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const { file_id, description }: { file_id: string; description: string } = await readBody(event)

  if (!file_id || !description) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid request: file_id and description are required',
    })
  }

  if (description.trim().length < 10) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Description must be at least 10 characters long',
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
    // Step 1: Check if there are already 3 non-pinned descriptions for this file
    const existingResult = await pool.query(
      `SELECT id FROM bre_descriptions 
       WHERE file_id = $1 AND pinned = FALSE 
       ORDER BY created_at ASC`,
      [file_id]
    )

    // If we already have 3+ non-pinned descriptions, remove the oldest
    if (existingResult.rows.length >= 3) {
      const oldestId = existingResult.rows[0].id
      await pool.query('DELETE FROM bre_descriptions WHERE id = $1', [oldestId])
    }

    // Step 2: Insert the new description (not pinned by default)
    const insertResult = await pool.query(
      `INSERT INTO bre_descriptions (file_id, description, pinned) 
       VALUES ($1, $2, FALSE) 
       RETURNING id, file_id, description, pinned, created_at`,
      [file_id, description.trim()]
    )

    return {
      success: true,
      description: insertResult.rows[0],
    }
  } catch (error: any) {
    console.error('[description-create] Error:', error)
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to create description: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
