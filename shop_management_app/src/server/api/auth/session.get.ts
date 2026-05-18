// Session Check API Endpoint
// Returns the current user's session information
// Includes display name from oc_accounts

import { eq } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { userAccounts, ocAccounts } from '~/lib/auth-schema'
import { getDisplayNameFromData } from '~/server/utils/auth'

export default defineEventHandler(async (event) => {
  // getUserSession is auto-imported by nuxt-auth-utils
  const session = await getUserSession(event)
  
  if (!session?.user?.id) {
    return { authenticated: false }
  }

  const db = getDb()
  
  // Get user account details
  const appUsers = await db
    .select()
    .from(userAccounts)
    .where(eq(userAccounts.id, session.user.id))
    .limit(1)

  if (!appUsers.length || !appUsers[0]?.isActive) {
    // Session exists but user account is invalid/deleted
    await clearUserSession(event)
    return { authenticated: false }
  }

  const appUser = appUsers[0]!

  // Get display name from oc_accounts
  const accounts = await db
    .select({ data: ocAccounts.data })
    .from(ocAccounts)
    .where(eq(ocAccounts.uid, appUser.nextcloudUid))
    .limit(1)

  let displayName = appUser.nextcloudUid
  if (accounts.length > 0 && accounts[0]?.data) {
    const name = getDisplayNameFromData(accounts[0].data)
    if (name) {
      displayName = name
    }
  }

  return {
    authenticated: true,
    user: {
      id: appUser.id,
      username: appUser.nextcloudUid,
      displayName: displayName,
      role: appUser.role,
      allowedGalleryIds: appUser.allowedGalleryIds || [],
    },
  }
})
