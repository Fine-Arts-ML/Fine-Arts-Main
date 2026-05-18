/**
 * Update Staged Item API
 * Updates a staged description or adds/removes a tag mapping.
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

  // Read request body
  const body = await readBody(event)
  const { operation, targetId, fileId, data }: {
    operation: 'update_description' | 'add_tag' | 'remove_tag'
    targetId: number
    fileId?: string
    data?: {
      description?: string
      tagName?: string
    }
  } = body || {}

  switch (operation) {
    case 'update_description': {
      // Update a staged description
      const existing = await db.select()
        .from(breDescriptionsStaging)
        .where(and(
          eq(breDescriptionsStaging.id, targetId),
          eq(breDescriptionsStaging.sessionId, sessionId)
        ))
        .limit(1)

      if (existing.length === 0) {
        throw createError({ statusCode: 404, statusMessage: 'Staged description not found' })
      }

      if (!data?.description) {
        throw createError({ statusCode: 400, statusMessage: 'Description text required' })
      }

      await db.update(breDescriptionsStaging)
        .set({ description: data.description })
        .where(eq(breDescriptionsStaging.id, targetId))

      return { success: true, id: targetId }
    }

    case 'add_tag': {
      // Add a tag to a file (or create the tag if it doesn't exist)
      const tagName = data?.tagName
      if (!tagName || !fileId) {
        throw createError({ statusCode: 400, statusMessage: 'tagName and fileId required' })
      }

      // Check if tag exists for this session
      const existingTag = await db.select()
        .from(breTagsStaging)
        .where(and(
          eq(breTagsStaging.sessionId, sessionId),
          eq(breTagsStaging.name, tagName)
        ))
        .limit(1)

      let tagId: number

      if (existingTag.length > 0) {
        tagId = existingTag[0].id
      } else {
        const inserted = await db.insert(breTagsStaging)
          .values({
            sessionId,
            name: tagName
          })
          .returning({ id: breTagsStaging.id })
        tagId = inserted[0].id
      }

      // Check if mapping already exists
      const existingMapping = await db.select()
        .from(breTagMapStaging)
        .where(and(
          eq(breTagMapStaging.sessionId, sessionId),
          eq(breTagMapStaging.tagId, tagId),
          eq(breTagMapStaging.fileId, fileId)
        ))
        .limit(1)

      if (existingMapping.length === 0) {
        await db.insert(breTagMapStaging).values({
          sessionId,
          tagId,
          fileId
        })
      }

      return { success: true, tagId }
    }

    case 'remove_tag': {
      // Remove a tag mapping (targetId = mapping.id)
      const existing = await db.select()
        .from(breTagMapStaging)
        .where(and(
          eq(breTagMapStaging.id, targetId),
          eq(breTagMapStaging.sessionId, sessionId)
        ))
        .limit(1)

      if (existing.length === 0) {
        throw createError({ statusCode: 404, statusMessage: 'Tag mapping not found' })
      }

      await db.delete(breTagMapStaging)
        .where(eq(breTagMapStaging.id, targetId))

      return { success: true, id: targetId }
    }

    default:
      throw createError({ statusCode: 400, statusMessage: `Unknown operation: ${operation}` })
  }
})
