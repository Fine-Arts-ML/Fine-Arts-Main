export default defineEventHandler(async () => {
  try {
    const pg = await import('pg')
    const pool = new pg.Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    })

    try {
      // Use bre_file_junction as the source of truth
      const result = await pool.query(
        `SELECT DISTINCT ON (ai.fileid, fj.shop_id)
          ai.fileid AS "fileId",
          ai.name AS "name",
          ai.preview_url AS "previewUrl",
          fj.shop_id AS "shopId",
          s.shop_name AS "shopName",
          fj.account_id AS "accountId",
          sa.account_name AS "accountName"
        FROM bre_advance_index ai
        INNER JOIN bre_file_junction fj ON ai.fileid::text = fj.file_id
        INNER JOIN bre_shops s ON fj.shop_id = s.shop_id
        INNER JOIN bre_shop_account sa ON fj.account_id = sa.account_id
        ORDER BY ai.fileid, fj.shop_id`
      )

      return (result as any).rows
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch files',
      data: error.message,
    })
  }
})
