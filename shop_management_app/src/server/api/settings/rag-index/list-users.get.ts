/**
 * List Users API
 * Returns all users with home storages from Nextcloud database
 * Includes role information from bre_user_accounts table
 * This allows the admin to filter users by role and select any user's home directory for indexing
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  try {
    // Connect directly to Nextcloud database using environment variables
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
      // Get all user home storages
      const usersResult = await pool.query(
        `SELECT 
          s.id AS storage_id,
          s.numeric_id,
          s.available,
          REPLACE(s.id, 'home::', '') AS uid
        FROM oc_storages s
        WHERE s.id LIKE 'home::%'
        ORDER BY s.id ASC`
      )

      // Get display names from oc_users table if it exists
      let displayNameMap = new Map<string, string>()
      try {
        const usersTableResult = await pool.query(
          `SELECT uid, display_name FROM oc_users`
        )
        usersTableResult.rows.forEach((row: any) => {
          displayNameMap.set(row.uid, row.display_name)
        })
      } catch {
        console.log('oc_users table not found, using uid as display name')
      }

      // Get user roles from bre_user_accounts table if it exists
      let roleMap = new Map<string, string>()
      try {
        const rolesResult = await pool.query(
          `SELECT nextcloud_uid, role FROM bre_user_accounts`
        )
        rolesResult.rows.forEach((row: any) => {
          roleMap.set(row.nextcloud_uid, row.role)
        })
      } catch {
        console.log('bre_user_accounts table not found, defaulting role to user')
      }

      // Combine all data
      const users = usersResult.rows.map((row: any) => ({
        uid: row.uid,
        storageId: parseInt(row.numeric_id),
        numericId: parseInt(row.numeric_id),
        available: row.available,
        displayName: displayNameMap.get(row.uid) || row.uid,
        role: roleMap.get(row.uid) || 'user', // Default to 'user' role
      }))

      return {
        users,
      }
    } finally {
      await pool.end()
    }
  } catch (error: any) {
    console.error('Error listing users:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Failed to list users',
    })
  }
})
