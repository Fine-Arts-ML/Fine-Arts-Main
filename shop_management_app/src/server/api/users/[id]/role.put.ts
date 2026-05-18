// PUT /api/users/:id/role
// Update a user's role
// Requires admin access

import { eq } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { userAccounts } from '~/lib/auth-schema'

const validRoles = ['guest', 'user', 'admin']

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
  const { role } = body

  if (!role || !validRoles.includes(role)) {
    throw createError({ statusCode: 400, statusMessage: `Invalid role. Must be one of: ${validRoles.join(', ')}` })
  }

  // Update the user's role
  const updated = await db
    .update(userAccounts)
    .set({ role })
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

  return {
    success: true,
    user: updated[0],
  }
})
