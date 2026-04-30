export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')

    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Shop ID is required',
      })
    }

    const shopId = parseInt(id, 10)
    if (isNaN(shopId)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid shop ID',
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
      // Use bre_file_junction as the source of truth for accounts with files
      const result = await pool.query(
        `SELECT
          sa.account_id AS "accountId",
          sa.account_name AS "accountName",
          COUNT(fj.file_id) AS "fileCount"
        FROM bre_shop_account sa
        INNER JOIN bre_file_junction fj ON sa.account_id = fj.account_id
        WHERE fj.shop_id = $1
        GROUP BY sa.account_id, sa.account_name
        ORDER BY sa.account_name`,
        [shopId]
      )

      return (result as any).rows
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch shop accounts',
      data: error.message,
    })
  }
})
