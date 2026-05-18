/**
 * Delete Staged Item API
 * Deletes a staged description or tag mapping.
 * Uses session-based isolation (session_id = userId from nuxt-auth-utils session).
 */
import { eq, and } from 'drizzle-orm'
import { breTagsStaging, breTagMapStaging, breDescriptionsStaging } from '~/lib/nextcloud-schema'
import { getDb } from '~/lib/db'

export default defineEventHandler(async (event: any) => {
  // Authenticate user
  const session = await getUserSession(event)
  if (!session?.user?.id) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const sessionId = String(session.user.id)
  const db = getDb()

  // Read query params
  const { type, id }: { type: 'description' | 'tag_mapping'; id: string } = getQuery(event)

  if (!type || !id) {
    throw createError({ statusCode: 400, statusMessage: 'type and id query params required' })
  }

  switch (type) {
    case 'description': {
      const existing = await db.select()
        .from(breDescriptionsStaging)
        .where(and(
          eq(breDescriptionsStaging.id, parseInt(id)),
          eq(breDescriptionsStaging.sessionId, sessionId)
        ))
        .limit(1)

      if (existing.length === 0) {
        throw createError({ statusCode: 404, statusMessage: 'Staged description not found' })
      }

      await db.delete(breDescriptionsStaging)
        .where(eq(breDescriptionsStaging.id, parseInt(id)))

      return { success: true, id: parseInt(id), type: 'description' }
    }

    case 'tag_mapping': {
      const existing = await db.select()
        .from(breTagMapStaging)
        .where(and(
          eq(breTagMapStaging.id, parseInt(id)),
          eq(breTagMapStaging.sessionId, sessionId)
        ))
        .limit(1)

      if (existing.length === 0) {
        throw createError({ statusCode: 404, statusMessage: 'Tag mapping not found' })
      }

      await db.delete(breTagMapStaging)
        .where(eq(breTagMapStaging.id, parseInt(id)))

      return { success: true, id: parseInt(id), type: 'tag_mapping' }
    }

    default:
      throw createError({ statusCode: 400, statusMessage: `Unknown type: ${type}` })
  }
})
