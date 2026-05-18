/**
 * Save Index Config API
 * Stores the selected index directory configuration including all selected folders
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  
  const { folders } = body
  
  try {
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
      // Build config value with only the folders array
      const configValue: { folders: Array<{ path: string; storageId: number; displayName: string }> } = {
        folders: folders || [],
      }

      console.log('[index-config.post] Saving config:', JSON.stringify(configValue))

      await pool.query(
        `INSERT INTO bre_index_config (config_key, config_value)
         VALUES ('selected_index_path', $1)
         ON CONFLICT (config_key)
         DO UPDATE SET config_value = $1, updated_at = NOW()`,
        [JSON.stringify(configValue)]
      )

      console.log('[index-config.post] Config saved successfully')

      return { success: true, config: configValue }
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    console.error('Error saving index config:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Failed to save index config',
    })
  }
})
