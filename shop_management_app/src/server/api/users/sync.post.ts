// POST /api/users/sync
// Sync all Nextcloud users to bre_user_accounts
// Creates entries for new users and updates roles for existing users
// Requires admin access

import { syncNextcloudUsers } from '~/server/utils/auth'
import { getDb } from '~/lib/db'

export default defineEventHandler(async (event) => {
  // Check admin access
  const session = await getUserSession(event)
  if (!session?.user?.id) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const db = getDb()
  const { userAccounts } = await import('~/lib/auth-schema')
  const { eq } = await import('drizzle-orm')

  const appUsers = await db
    .select({ role: userAccounts.role })
    .from(userAccounts)
    .where(eq(userAccounts.id, session.user.id))
    .limit(1)

  if (!appUsers.length || appUsers[0]?.role !== 'admin') {
    throw createError({ statusCode: 403, statusMessage: 'Admin access required' })
  }

  // Perform sync
  const results = await syncNextcloudUsers()

  return {
    success: true,
    ...results,
  }
})
