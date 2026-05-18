// Seed Admin Endpoint
// Creates an admin account from an existing Nextcloud user
// This endpoint should only be called once during initial setup
// After setup, set SEED_ADMIN_ENABLED=false in .env to disable this endpoint
//
// Usage (first time only):
//   curl -X POST http://localhost:3000/api/auth/seed-admin \
//     -H "Content-Type: application/json" \
//     -d '{"nextcloudUsername": "Tom"}'

import { eq } from 'drizzle-orm'
import { ocUsers, userAccounts } from '~/lib/auth-schema'
import { getDb } from '~/lib/db'

export default defineEventHandler(async (event) => {
  // Check if seed admin is enabled (disable after initial setup)
  const seedEnabled = process.env.SEED_ADMIN_ENABLED !== 'false'
  
  if (!seedEnabled) {
    throw createError({ 
      statusCode: 403, 
      statusMessage: 'Admin seeding is disabled. Set SEED_ADMIN_ENABLED=true to enable.' 
    })
  }

  const body = await readBody(event)
  const { username } = body

  if (!username) {
    throw createError({ statusCode: 400, statusMessage: 'Username is required' })
  }

  const db = getDb()

  // 1. Check if user exists in Nextcloud
  const ncUsers = await db
    .select()
    .from(ocUsers)
    .where(eq(ocUsers.uid, username))
    .limit(1)

  if (!ncUsers.length) {
    throw createError({ statusCode: 404, statusMessage: 'Nextcloud user not found' })
  }

  // 2. Check if user already exists in our system
  const existingUsers = await db
    .select()
    .from(userAccounts)
    .where(eq(userAccounts.nextcloudUid, username))
    .limit(1)

  if (existingUsers.length) {
    // Update role to admin if already exists
    await db
      .update(userAccounts)
      .set({ role: 'admin', updatedAt: new Date().toISOString() })
      .where(eq(userAccounts.nextcloudUid, username))
    
    return { 
      success: true, 
      message: `User ${username} updated to admin`, 
      role: 'admin',
      note: 'Admin seeding is now disabled. Set SEED_ADMIN_ENABLED=true to re-enable.'
    }
  }

  // 3. Create admin account
  const newUsers = await db
    .insert(userAccounts)
    .values({
      nextcloudUid: username,
      role: 'admin',
      allowedGalleryIds: [],
      isActive: true,
    })
    .returning()

  const appUser = newUsers[0]
  
  if (!appUser) {
    throw createError({ statusCode: 500, statusMessage: 'Failed to create admin account' })
  }
  
  return { 
    success: true, 
    message: `Admin account created for ${username}`, 
    role: 'admin',
    note: 'Admin seeding is now disabled. Set SEED_ADMIN_ENABLED=true to re-enable.'
  }
})
