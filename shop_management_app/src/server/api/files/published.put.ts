import { Pool } from 'pg'

let pool: Pool | null = null

function getPool(): Pool {
  if (!pool) {
    const dbHost = process.env.DB_HOST || 'localhost'
    const dbPort = Number(process.env.DB_PORT) || 5432
    const dbName = process.env.DB_NAME || 'shop_management'
    const dbUser = process.env.DB_USER || 'postgres'
    const dbPassword = process.env.DB_PASSWORD || 'postgres'

    pool = new Pool({
      host: dbHost,
      port: dbPort,
      database: dbName,
      user: dbUser,
      password: dbPassword,
    })
  }
  return pool
}

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { fileId, shopId, published } = body

    if (!fileId || !shopId || published === undefined) {
      throw createError({
        statusCode: 400,
        statusMessage: 'fileId, shopId, and published are required',
      })
    }

    const dbPool = getPool()
    
    // Update the published status in bre_file_junction
    await dbPool.query(
      'UPDATE bre_file_junction SET published = $1 WHERE file_id = $2 AND shop_id = $3',
      [published, String(fileId), shopId]
    )

    return { status: 'success' }
  } catch (e: any) {
    console.error('[published.put] Error:', e)
    throw createError({
      statusCode: 500,
      statusMessage: e.statusMessage || 'Failed to update published status',
    })
  }
})
