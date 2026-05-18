/**
 * Toggle Description Pin API
 * Toggles the pinned status of a description in bre_descriptions.
 * Enforces: max 1 pinned description per file (unpins others when pinning).
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const { descriptionId, pinned }: { descriptionId: number; pinned: boolean } = await readBody(event)

  if (!descriptionId || typeof pinned !== 'boolean') {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid request: descriptionId and pinned are required',
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
    // Step 1: Get the file_id for this description
    const descResult = await pool.query(
      'SELECT file_id FROM bre_descriptions WHERE id = $1',
      [descriptionId]
    )

    if (descResult.rows.length === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Description not found',
      })
    }

    const fileId: string = descResult.rows[0].file_id

    // Step 2: If pinning, unpin all other descriptions for this file
    if (pinned) {
      await pool.query(
        'UPDATE bre_descriptions SET pinned = FALSE WHERE file_id = $1 AND id != $2',
        [fileId, descriptionId]
      )
    }

    // Step 3: Toggle the pinned status
    await pool.query(
      'UPDATE bre_descriptions SET pinned = $1 WHERE id = $2',
      [pinned, descriptionId]
    )

    // Step 4: Return updated description
    const updatedResult = await pool.query(
      'SELECT id, file_id, description, pinned, created_at FROM bre_descriptions WHERE id = $1',
      [descriptionId]
    )

    return {
      success: true,
      description: updatedResult.rows[0],
    }
  } catch (error: any) {
    console.error('[description-pin] Error:', error)
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to toggle pin: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
