// PUT /api/users/:id/active
// Toggle a user's active status
// Requires admin access

import { eq } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { userAccounts } from '~/lib/auth-schema'

export default defineEventHandler(async (event) => {
  // Check admin access
  const session = await getUserSession(event)
  if (!session?.user?.id) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const db = getDb()
  const adminUsers = await db
    .select({ role: userAccounts.role })
    .from(userAccounts)
    .where(eq(userAccounts.id, session.user.id))
    .limit(1)

  if (!adminUsers.length || adminUsers[0]?.role !== 'admin') {
    throw createError({ statusCode: 403, statusMessage: 'Admin access required' })
  }

  const id = getRouterParam(event, 'id')
  const body = await readBody(event)
  const { isActive } = body

  if (typeof isActive !== 'boolean') {
    throw createError({ statusCode: 400, statusMessage: 'isActive must be a boolean' })
  }

  // Prevent admin from deactivating themselves
  if (parseInt(id) === session.user.id && isActive === false) {
    throw createError({ statusCode: 400, statusMessage: 'You cannot deactivate your own account' })
  }

  // Update the user's active status
  const updated = await db
    .update(userAccounts)
    .set({ isActive })
    .where(eq(userAccounts.id, parseInt(id)))
    .returning({
      id: userAccounts.id,
      nextcloudUid: userAccounts.nextcloudUid,
      role: userAccounts.role,
      isActive: userAccounts.isActive,
    })

  if (!updated.length) {
    throw createError({ statusCode: 404, statusMessage: 'User not found' })
  }

  // If deactivating, clear the user's session if it's the current user
  if (isActive === false && parseInt(id) === session.user.id) {
    await clearUserSession(event)
  }

  return {
    success: true,
    user: updated[0],
  }
})
