// Login API Endpoint
// Authenticates users against Nextcloud database and creates a session
// Enforces admin-provisioned access: only pre-synced users can log in
// Syncs role from Nextcloud groups on every login

import { eq } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { verifyNextcloudPassword, getUserNextcloudGroups, getRoleFromGroups } from '~/server/utils/auth'
import { ocUsers, userAccounts } from '~/lib/auth-schema'

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { username, password } = body

  if (!username || !password) {
    throw createError({ statusCode: 400, statusMessage: 'Username and password are required' })
  }

  const db = getDb()

  // 1. Query Nextcloud users table for the username
  const ncUsers = await db
    .select()
    .from(ocUsers)
    .where(eq(ocUsers.uid, username))
    .limit(1)

  if (!ncUsers.length) {
    throw createError({ statusCode: 401, statusMessage: 'Invalid credentials' })
  }

  const ncUser = ncUsers[0]
  if (!ncUser) {
    throw createError({ statusCode: 401, statusMessage: 'Invalid credentials' })
  }

  // 2. Verify password against Nextcloud hash
  const isValid = await verifyNextcloudPassword(password, ncUser.password)
  if (!isValid) {
    throw createError({ statusCode: 401, statusMessage: 'Invalid credentials' })
  }

  // 3. Check if user exists in our app's bre_user_accounts table (admin-provisioned)
  const appUsers = await db
    .select()
    .from(userAccounts)
    .where(eq(userAccounts.nextcloudUid, username))
    .limit(1)

  if (!appUsers.length) {
    // User has valid Nextcloud credentials but is not provisioned in the app
    throw createError({ statusCode: 403, statusMessage: 'Account not provisioned. Contact the administrator.' })
  }

  const appUser = appUsers[0]!
  
  // Check if user is active
  if (!appUser.isActive) {
    throw createError({ statusCode: 403, statusMessage: 'Account deactivated. Contact the administrator.' })
  }

  // 4. Sync role from Nextcloud groups (real-time group changes reflected on login)
  const groups = await getUserNextcloudGroups(username)
  const defaultRole = process.env.DEFAULT_ROLE || 'user'
  const calculatedRole = getRoleFromGroups(groups, defaultRole)
  let currentRole = appUser.role
  
  if (currentRole !== calculatedRole) {
    currentRole = calculatedRole
    await db
      .update(userAccounts)
      .set({ role: calculatedRole })
      .where(eq(userAccounts.id, appUser.id))
  }

  // 5. Create session (auto-imported by nuxt-auth-utils)
  await setUserSession(event, {
    user: {
      id: appUser.id,
      nextcloudUid: appUser.nextcloudUid,
      role: currentRole,
    },
  })

  return {
    success: true,
    user: {
      id: appUser.id,
      username: appUser.nextcloudUid,
      role: currentRole,
    }
  }
})
