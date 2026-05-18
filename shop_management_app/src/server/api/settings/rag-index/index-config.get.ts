/**
 * Get Index Config API
 * Returns the currently selected index directory configuration including all selected folders
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
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
      const result = await pool.query(
        `SELECT config_value FROM bre_index_config WHERE config_key = 'selected_index_path'`
      )

      if (result.rows.length === 0) {
        return {
          userId: null,
          path: '',
          storageId: null,
          selectedAt: null,
          folders: [],
        }
      }

      const config = result.rows[0].config_value
      
      // Ensure folders array exists for backward compatibility
      if (!config.folders && config.path) {
        config.folders = [{
          path: config.path,
          userId: config.userId,
          storageId: config.storageId,
          displayName: config.path,
        }]
      }
      
      return config
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    console.error('Error getting index config:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Failed to get index config',
    })
  }
})
