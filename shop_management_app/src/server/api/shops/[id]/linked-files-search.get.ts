import { transformPreviewUrls } from '~/server/utils/preview'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const query = getQuery(event).query as string | undefined
    const accountId = getQuery(event).accountId as string | undefined
    const limit = parseInt(getQuery(event).limit as string || '15', 10)
    const offset = parseInt(getQuery(event).offset as string || '0', 10)
    const previewSize = parseInt(getQuery(event).previewSize as string || '64', 10)
    const publishedFilter = getQuery(event).published as string | undefined

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

    console.log(`[linked-files-search] shopId=${shopId}, accountId=${accountId}, query=${query}, limit=${limit}, offset=${offset}, publishedFilter=${publishedFilter}`)

    const searchQuery = query ? `%${query.trim()}%` : null
    const hasSearchQuery = !!query && query.trim().length > 0

    // Use raw SQL with parameterized query using bre_file_junction as the source of truth
    // Build params array: [shopId, accountId?, searchQuery?, publishedFilter?, limit, offset]
    const params: (string | number | boolean)[] = [shopId]
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

    if (publishedFilter) {
      if (publishedFilter === 'true') {
        whereClauses.push(`fj.published = $${paramNum}::boolean`)
        params.push(true)
        paramNum++
      } else {
        // 'false' filter: match both false AND NULL values (no parameter needed)
        whereClauses.push(`fj.published IS NOT true`)
      }
    }

    if (hasSearchQuery && searchQuery) {
      whereClauses.push(`(ai.name ILIKE $${paramNum} OR dn.display_name ILIKE $${paramNum})`)
      params.push(searchQuery)
      paramNum++
    }

    // Add limit and offset params
    params.push(limit, offset)
    const limitOffsetClause = `LIMIT $${paramNum} OFFSET $${paramNum + 1}`

    const whereClause = whereClauses.join(' AND ')

    // New query using bre_file_junction as the primary filter
    // Aggregates all account names per file using a subquery
    // Returns published status from bre_file_junction using BOOL_OR (PostgreSQL boolean OR aggregate)
    const rawQuery = `
      SELECT
        ai.fileid AS "fileId",
        ai.name AS "filename",
        ai.preview_url AS "previewUrl",
        BOOL_OR(fj.published) AS "published",
        MAX(dn.display_name) AS "displayName",
        (ARRAY_AGG(DISTINCT fj.account_id)) AS "accountIds",
        (
          SELECT ARRAY_AGG(DISTINCT sa2.account_name ORDER BY sa2.account_name)
          FROM bre_file_junction fj2
          JOIN bre_shop_account sa2 ON fj2.account_id = sa2.account_id
          WHERE fj2.file_id = ai.fileid AND fj2.shop_id = $1
        ) AS "accountNames"
      FROM bre_advance_index ai
      INNER JOIN bre_file_junction fj ON ai.fileid::text = fj.file_id
      INNER JOIN bre_shop_account sa ON fj.account_id = sa.account_id
      LEFT JOIN bre_display_name_index dni ON ai.fileid::text = dni.file_id
      LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
      WHERE ${whereClause}
      GROUP BY ai.fileid, ai.name, ai.preview_url
      ORDER BY ai.fileid
      ${limitOffsetClause}
    `

    console.log('[linked-files-search] Raw query:', rawQuery)
    console.log('[linked-files-search] Params:', params)

    const pg = await import('node_modules/@types/pg')
    const pool = new pg.Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    })

    const result = await pool.query(rawQuery, params)
    const rows = (result as any).rows
    console.log(`[linked-files-search] Result count:`, rows.length)

    // Transform preview URLs to absolute URLs with actual dimensions
    const transformedRows = transformPreviewUrls(rows, previewSize)

    await pool.end()

    return transformedRows
  } catch (error: any) {
    console.error('[linked-files-search] Error:', error)
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch linked files',
      data: error.message,
    })
  }
})
