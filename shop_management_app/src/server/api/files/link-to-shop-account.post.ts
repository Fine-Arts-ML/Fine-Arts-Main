/**
 * Link a file to both a shop and an account.
 *
 * Request body:
 *   - fileId: File ID (required)
 *   - shopId: Shop ID (required)
 *   - accountId: Account ID (required)
 *   - published: Whether the file is published/available for purchase (default: false)
 *   - displayNames: Array of display name strings (optional)
 *
 * Inserts into:
 *   - bre_file_junction (triadic relationship: shop + file + account)
 *   - bre_display_names (display name entries)
 *   - bre_display_name_index (display name → shop/account/file mapping)
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { fileId, shopId, accountId, published = false, displayNames = [] } = body

  if (!fileId || !shopId || !accountId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'fileId, shopId, and accountId are required',
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
    // Insert into junction table (triadic relationship)
    // ON CONFLICT DO NOTHING prevents duplicate entries
    await pool.query(
      'INSERT INTO bre_file_junction (shop_id, file_id, account_id, published) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING',
      [shopId, String(fileId), accountId, published]
    )

    // Insert display names if provided
    console.log(`[link-to-shop-account] displayNames received:`, displayNames)
    if (displayNames.length > 0) {
      for (const displayName of displayNames) {
        console.log(`[link-to-shop-account] Processing display name: ${displayName}`)
        // First, check if the display name already exists
        const existingResult = await pool.query(
          'SELECT display_name_id FROM bre_display_names WHERE display_name = $1',
          [displayName]
        )

        let displayNameId: number
        if (existingResult.rows.length > 0) {
          // Display name already exists, use the existing ID
          displayNameId = existingResult.rows[0].display_name_id
          console.log(`[link-to-shop-account] Found existing display_name_id: ${displayNameId}`)
        } else {
          // Display name does not exist, insert a new one
          console.log(`[link-to-shop-account] Display name not found, inserting new...`)
          const insertResult = await pool.query(
            'INSERT INTO bre_display_names (display_name) VALUES ($1) RETURNING display_name_id',
            [displayName]
          )
          if (insertResult.rows.length > 0) {
            displayNameId = insertResult.rows[0].display_name_id
            console.log(`[link-to-shop-account] Inserted new display_name_id: ${displayNameId}`)
          } else {
            // Edge case: continue if insertion failed
            console.log(`[link-to-shop-account] WARNING: Insert returned no rows`)
            continue
          }
        }

        // Insert into display name index matrix
        console.log(`[link-to-shop-account] Inserting into bre_display_name_index: displayNameId=${displayNameId}, shopId=${shopId}, accountId=${accountId}, fileId=${String(fileId)}`)
        await pool.query(
          'INSERT INTO bre_display_name_index (display_name_id, shop_id, account_id, file_id) VALUES ($1, $2, $3, $4)',
          [displayNameId, shopId, accountId, String(fileId)]
        )
        console.log(`[link-to-shop-account] Successfully inserted into bre_display_name_index`)
      }
    }

    return { success: true, fileId, shopId, accountId, displayNamesAdded: displayNames.length }
  } finally {
    await pool.end()
  }
})
