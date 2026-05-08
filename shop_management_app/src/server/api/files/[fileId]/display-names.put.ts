/**
 * Update display names for a file.
 *
 * Request body:
 *   - shopId: Shop ID (required)
 *   - newDisplayNames: Array of display name strings (required)
 *
 * Behavior:
 *   - Adds new display names (creates entries in bre_display_names + bre_display_name_index)
 *   - Removes display names that are no longer in the list (deletes from bre_display_name_index)
 *   - Does NOT modify existing display names (renaming requires delete + insert)
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { fileId, shopId, newDisplayNames } = body

  if (!fileId || !shopId || !Array.isArray(newDisplayNames)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'fileId, shopId, and newDisplayNames (array) are required',
    })
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
    const fileIdStr = String(fileId)

    // Get currently linked display name IDs for this file+shop
    const currentResult = await pool.query(
      `SELECT dn.display_name_id, dn.display_name
       FROM bre_display_name_index dni
       JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
       WHERE dni.file_id = $1 AND dni.shop_id = $2`,
      [fileIdStr, shopId]
    )

    const currentDisplayNames = new Set(currentResult.rows.map((row: any) => row.display_name))
    const newDisplayNamesSet = new Set(newDisplayNames.map((n: string) => n.trim()).filter(Boolean))

    // Display names to remove (exist but not in new list)
    const toRemove = currentResult.rows.filter((row: any) => !newDisplayNamesSet.has(row.display_name))
    // Display names to add (in new list but not exist)
    const toAdd = newDisplayNames.filter((n: string) => {
      const trimmed = n.trim()
      return trimmed && !currentDisplayNames.has(trimmed)
    })

    // Remove old display name index entries
    for (const row of toRemove) {
      await pool.query(
        'DELETE FROM bre_display_name_index WHERE file_id = $1 AND shop_id = $2 AND display_name_id = $3',
        [fileIdStr, shopId, row.display_name_id]
      )
    }

    // Add new display names
    for (const displayName of toAdd) {
      // Check if display name already exists
      const existingResult = await pool.query(
        'SELECT display_name_id FROM bre_display_names WHERE display_name = $1',
        [displayName]
      )

      let displayNameId: number
      if (existingResult.rows.length > 0) {
        displayNameId = existingResult.rows[0].display_name_id
      } else {
        // Insert new display name
        const insertResult = await pool.query(
          'INSERT INTO bre_display_names (display_name) VALUES ($1) RETURNING display_name_id',
          [displayName]
        )
        if (insertResult.rows.length > 0) {
          displayNameId = insertResult.rows[0].display_name_id
        } else {
          continue
        }
      }

      // Insert into display name index
      await pool.query(
        'INSERT INTO bre_display_name_index (display_name_id, shop_id, account_id, file_id) VALUES ($1, $2, (SELECT account_id FROM bre_file_junction WHERE file_id = $3 AND shop_id = $4 LIMIT 1), $5)',
        [displayNameId, shopId, fileIdStr, shopId, fileIdStr]
      )
    }

    return {
      success: true,
      removed: toRemove.length,
      added: toAdd.length,
      total: newDisplayNamesSet.size,
    }
  } finally {
    await pool.end()
  }
})
