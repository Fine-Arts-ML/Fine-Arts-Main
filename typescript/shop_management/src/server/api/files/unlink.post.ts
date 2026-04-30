/**
 * Unlink a file from a shop and optionally an account.
 *
 * Request body:
 *   - fileId: File ID (required)
 *   - shopId: Shop ID (required)
 *   - accountId: Account ID (optional - if provided, only unlink from account;
 *                if omitted, unlink from shop entirely across all accounts)
 *
 * Deletes from:
 *   - bre_file_junction (triadic relationship table)
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { fileId, shopId, accountId } = body

  if (!fileId || !shopId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'fileId and shopId are required',
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
    if (accountId) {
      // Unlink specific file from shop + account combination
      await pool.query(
        'DELETE FROM bre_file_junction WHERE shop_id = $1 AND file_id = $2 AND account_id = $3',
        [shopId, String(fileId), accountId]
      )
    } else {
      // Unlink file from shop entirely (all accounts)
      await pool.query(
        'DELETE FROM bre_file_junction WHERE shop_id = $1 AND file_id = $2',
        [shopId, String(fileId)]
      )
    }

    return { success: true, fileId, shopId, accountId }
  } finally {
    await pool.end()
  }
})
