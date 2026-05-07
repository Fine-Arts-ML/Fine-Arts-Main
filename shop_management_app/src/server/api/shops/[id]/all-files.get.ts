export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const accountId = getQuery(event).accountId as string | undefined
    const limit = parseInt(getQuery(event).limit as string || '50', 10)
    const offset = parseInt(getQuery(event).offset as string || '0', 10)

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

    // Build params array: [shopId, accountId?, limit, offset]
    const params: (string | number)[] = [shopId]
    let paramNum = 2

    let whereClauses = ['fj.shop_id = $1']

    if (accountId) {
      const accountNumId = parseInt(accountId, 10)
      if (isNaN(accountNumId)) {
        throw createError({
          statusCode: 400,
          statusMessage: 'Invalid account ID',
        })
      }
      whereClauses.push(`fj.account_id = $${paramNum}`)
      params.push(accountNumId)
      paramNum++
    }

    // Add limit and offset params
    params.push(limit, offset)
    const limitOffsetClause = `LIMIT $${paramNum} OFFSET $${paramNum + 1}`

    const whereClause = whereClauses.join(' AND ')

    const pg = await import('node_modules/@types/pg')
    const pool = new pg.Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    })

    try {
      // Use bre_file_junction as the entry point
      const result = await pool.query(
        `SELECT DISTINCT ON (ai.fileid)
          ai.fileid AS "fileId",
          ai.name AS "filename",
          ai.preview_url AS "previewUrl",
          fj.account_id AS "accountId",
          sa.account_name AS "accountName"
        FROM bre_advance_index ai
        INNER JOIN bre_file_junction fj ON ai.fileid::text = fj.file_id
        INNER JOIN bre_shop_account sa ON fj.account_id = sa.account_id
        WHERE ${whereClause}
        ORDER BY ai.fileid
        ${limitOffsetClause}`,
        params
      )

      return (result as any).rows
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch files',
      data: error.message,
    })
  }
})
