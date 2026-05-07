/**
 * Link a file to both a shop and an account.
 *
 * Request body:
 *   - fileId: File ID (required)
 *   - shopId: Shop ID (required)
 *   - accountId: Account ID (required)
 *   - published: Whether the file is published/available for purchase (default: false)
 *
 * Inserts into:
 *   - bre_file_junction (triadic relationship: shop + file + account)
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { fileId, shopId, accountId, published = false } = body

  if (!fileId || !shopId || !accountId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'fileId, shopId, and accountId are required',
    })
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
    // Insert into junction table (triadic relationship)
    // ON CONFLICT DO NOTHING prevents duplicate entries
    await pool.query(
      'INSERT INTO bre_file_junction (shop_id, file_id, account_id, published) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING',
      [shopId, String(fileId), accountId, published]
    )

    return { success: true, fileId, shopId, accountId }
  } finally {
    await pool.end()
  }
})
