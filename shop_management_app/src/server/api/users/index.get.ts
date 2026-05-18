// GET /api/users
// List all users with optional search, role, and active status filters
// Requires admin access

import { eq, ilike, or, asc } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { userAccounts, ocAccounts, ocGroupUser } from '~/lib/auth-schema'
import { getDisplayNameFromData, getEmailFromData } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  // Only admins can access this endpoint
  if (!await isAdminCheck(event)) {
    throw createError({ statusCode: 403, statusMessage: 'Admin access required' })
  }

  const query = getQuery(event)
  const db = getDb()

  // Build search condition
  const searchQuery = (query.search as string) || ''
  const roleFilter = (query.role as string) || 'all'
  const activeFilter = (query.active as string) || 'all'

  // Get all users from bre_user_accounts
  let dbQuery = db.select().from(userAccounts).orderBy(asc(userAccounts.nextcloudUid))

  // Apply role filter
  if (roleFilter !== 'all') {
    dbQuery = dbQuery.where(eq(userAccounts.role, roleFilter))
  }

  // Apply active filter
  if (activeFilter === 'true') {
    dbQuery = dbQuery.where(eq(userAccounts.isActive, true))
  } else if (activeFilter === 'false') {
    dbQuery = dbQuery.where(eq(userAccounts.isActive, false))
  }

  const appUsers = await dbQuery

  // Enrich with oc_accounts data and group info
  const enrichedUsers = []

  for (const user of appUsers) {
    // Get display name and email from oc_accounts
    const accounts = await db
      .select({ data: ocAccounts.data })
      .from(ocAccounts)
      .where(eq(ocAccounts.uid, user.nextcloudUid))
      .limit(1)

    let displayName = user.nextcloudUid
    let email = ''

    if (accounts.length > 0 && accounts[0]?.data) {
      displayName = getDisplayNameFromData(accounts[0].data) || user.nextcloudUid
      email = getEmailFromData(accounts[0].data)
    }

    // Get groups for this user
    const groups = await db
      .select({ gid: ocGroupUser.gid })
      .from(ocGroupUser)
      .where(eq(ocGroupUser.uid, user.nextcloudUid))
    
    const groupNames = groups.map(g => g.gid)

    // Apply search filter (client-side filtering for display name and username)
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase()
      const matchesSearch = 
        user.nextcloudUid.toLowerCase().includes(searchLower) ||
        displayName.toLowerCase().includes(searchLower) ||
        email.toLowerCase().includes(searchLower)
      
      if (!matchesSearch) continue
    }

    enrichedUsers.push({
      id: user.id,
      nextcloudUid: user.nextcloudUid,
      displayName: displayName,
      email: email,
      role: user.role,
      allowedGalleryIds: user.allowedGalleryIds || [],
      isActive: user.isActive,
      nextcloudGroups: groupNames,
      createdAt: user.createdAt?.toISOString() || new Date().toISOString(),
      updatedAt: user.updatedAt?.toISOString() || new Date().toISOString(),
    })
  }

  return {
    users: enrichedUsers,
    total: enrichedUsers.length,
  }
})

// Helper function to check admin access
async function isAdminCheck(event: any): Promise<boolean> {
  const session = await getUserSession(event)
  if (!session?.user?.id) return false

  const db = getDb()
  const users = await db
    .select({ role: userAccounts.role })
    .from(userAccounts)
    .where(eq(userAccounts.id, session.user.id))
    .limit(1)

  return users.length > 0 && users[0]?.role === 'admin'
}
