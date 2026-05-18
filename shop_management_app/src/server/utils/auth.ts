// Authentication utilities
// Handles password verification against Nextcloud Argon2id hashes
// Handles Nextcloud group-based role synchronization

import { verify as argonVerify } from '@node-rs/argon2'
import { eq, asc } from 'drizzle-orm'
import { getDb } from '~/lib/db'
import { userAccounts, ocGroupUser, ocGroups, ocAccounts } from '~/lib/auth-schema'
import { sql } from 'drizzle-orm'

/**
 * Verify a password against a Nextcloud Argon2id hash.
 * Renamed from verifyPassword to avoid conflict with nuxt-auth-utils.
 */
export async function verifyNextcloudPassword(plainPassword: string, hash: string): Promise<boolean> {
  try {
    if (!hash.startsWith('3|$argon2id$')) {
      console.error('[auth] Unsupported password hash type:', hash.substring(0, 10))
      return false
    }

    const fullHash = hash.substring(2)
    return await argonVerify(fullHash, Buffer.from(plainPassword, 'utf-8'))
  } catch (error) {
    console.error('[auth] Password verification error:', error)
    return false
  }
}

/**
 * Get the current user's role from the session.
 */
export async function getUserRoleFromSession(event: any) {
  // getUserSession is auto-imported by nuxt-auth-utils
  const session = await getUserSession(event)
  
  if (!session?.userId) {
    return null
  }

  const db = getDb()
  const user = await db
    .select()
    .from(userAccounts)
    .where(eq(userAccounts.id, session.userId))
    .limit(1)

  if (!user.length || !user[0]?.isActive) {
    return null
  }

  const userData = user[0]
  return {
    id: userData.id,
    nextcloudUid: userData.nextcloudUid,
    role: userData.role,
    allowedGalleryIds: userData.allowedGalleryIds || [],
  }
}

/**
 * Check if the current user has the required role.
 * Role hierarchy: admin > user > guest
 */
export function hasRole(userRole: string | null, requiredRole: string): boolean {
  const roleHierarchy = { guest: 0, user: 1, admin: 2 }
  const userLevel = roleHierarchy[userRole as keyof typeof roleHierarchy] ?? -1
  const requiredLevel = roleHierarchy[requiredRole as keyof typeof roleHierarchy] ?? -1
  
  return userLevel >= requiredLevel
}

/**
 * Get all Nextcloud groups for a user.
 */
export async function getUserNextcloudGroups(uid: string): Promise<string[]> {
  const db = getDb()
  const groups = await db
    .select({ gid: ocGroupUser.gid })
    .from(ocGroupUser)
    .where(eq(ocGroupUser.uid, uid))
    .orderBy(asc(ocGroupUser.gid))
  return groups.map(g => g.gid)
}

/**
 * Determine role based on Nextcloud group membership.
 * Priority: Guest group > admin group > default (user)
 */
export function getRoleFromGroups(groupIds: string[], defaultRole: string): 'guest' | 'user' | 'admin' {
  if (groupIds.includes('Guest')) return 'guest'
  if (groupIds.includes('admin')) return 'admin'
  return (defaultRole === 'guest' || defaultRole === 'admin' ? defaultRole : 'user') as 'guest' | 'user' | 'admin'
}

/**
 * Get display name from oc_accounts JSON data.
 */
export function getDisplayNameFromData(data: string): string {
  try {
    const parsed = JSON.parse(data)
    return parsed.displayname?.value || ''
  } catch {
    return ''
  }
}

/**
 * Get email from oc_accounts JSON data.
 */
export function getEmailFromData(data: string): string {
  try {
    const parsed = JSON.parse(data)
    return parsed.email?.value || ''
  } catch {
    return ''
  }
}

/**
 * Get all Nextcloud users with their account data.
 */
export async function getAllNextcloudUsers() {
  const db = getDb()
  const accounts = await db
    .select({
      uid: ocAccounts.uid,
      data: ocAccounts.data,
    })
    .from(ocAccounts)
    .orderBy(asc(ocAccounts.uid))
  return accounts
}

/**
 * Sync all Nextcloud users to bre_user_accounts.
 * Creates entries for new users and updates roles for existing users.
 */
export async function syncNextcloudUsers() {
  const db = getDb()
  const defaultRole = process.env.DEFAULT_ROLE || 'user'

  // Get all Nextcloud accounts
  const accounts = await getAllNextcloudUsers()
  
  // Get all group memberships
  const groupMemberships = await db
    .select({
      uid: ocGroupUser.uid,
      gid: ocGroupUser.gid,
    })
    .from(ocGroupUser)
  
  // Get all existing bre_user_accounts entries
  const existingAccounts = await db
    .select({
      id: userAccounts.id,
      nextcloudUid: userAccounts.nextcloudUid,
      role: userAccounts.role,
    })
    .from(userAccounts)

  const existingMap = new Map(existingAccounts.map(a => [a.nextcloudUid, a]))
  const groupMap = new Map<string, string[]>()
  
  // Build group map: uid -> [groupIds]
  for (const membership of groupMemberships) {
    const existing = groupMap.get(membership.uid) || []
    existing.push(membership.gid)
    groupMap.set(membership.uid, existing)
  }

  const results = {
    synced: 0,
    created: 0,
    updated: 0,
    errors: [] as string[],
  }

  for (const account of accounts) {
    const uid = account.uid
    const groups = groupMap.get(uid) || []
    const role = getRoleFromGroups(groups, defaultRole)
    const existing = existingMap.get(uid)

    try {
      if (!existing) {
        // Create new entry
        await db.insert(userAccounts).values({
          nextcloudUid: uid,
          role: role,
          isActive: true,
        })
        results.created++
        results.synced++
      } else {
        // Update role if changed
        if (existing.role !== role) {
          await db
            .update(userAccounts)
            .set({ role })
            .where(eq(userAccounts.id, existing.id))
          results.updated++
          results.synced++
        } else {
          results.synced++
        }
      }
    } catch (error) {
      console.error(`[sync] Error syncing user ${uid}:`, error)
      results.errors.push(`Failed to sync ${uid}: ${error}`)
    }
  }

  return results
}
