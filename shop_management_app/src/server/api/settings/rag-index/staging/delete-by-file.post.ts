/**
 * Delete Staged Items by File ID API
 * Deletes all staged tags and/or descriptions for specified file IDs.
 * Uses session-based isolation (session_id = userId from nuxt-auth-utils session).
 *
 * Supports:
 * - Single file deletion
 * - Bulk file deletion
 * - Type filtering: tags, descriptions, or both
 * - Automatic orphan cleanup (removes empty tags after tag mapping deletion)
 */
import { eq, and, inArray } from 'drizzle-orm'
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
  const { file_ids, type }: {
    file_ids: string[]
    type: 'tags' | 'descriptions' | 'both'
  } = body || {}

  if (!file_ids || file_ids.length === 0) {
    throw createError({ statusCode: 400, statusMessage: 'file_ids required' })
  }
  if (!type || !['tags', 'descriptions', 'both'].includes(type)) {
    throw createError({ statusCode: 400, statusMessage: 'type must be tags, descriptions, or both' })
  }

  const results = {
    tagsDeleted: 0,
    mappingsDeleted: 0,
    descriptionsDeleted: 0,
    orphansCleaned: 0,
    errors: [] as string[]
  }

  // Process tags: delete mappings and clean up orphaned tags
  if (type === 'tags' || type === 'both') {
    try {
      // Step 1: Get all tag IDs that will be affected by mapping deletion
      const mappingsToDelete = await db.select({
        tagId: breTagMapStaging.tagId
      })
      .from(breTagMapStaging)
      .where(and(
        eq(breTagMapStaging.sessionId, sessionId),
        inArray(breTagMapStaging.fileId, file_ids)
      ))

      const tagIdsToDelete = new Set(mappingsToDelete.map((m: any) => m.tagId))

      // Step 2: Delete tag mappings for specified files
      const deletedMappings = await db.delete(breTagMapStaging)
        .where(and(
          eq(breTagMapStaging.sessionId, sessionId),
          inArray(breTagMapStaging.fileId, file_ids)
        ))
      results.mappingsDeleted = Number(deletedMappings) || 0

      // Step 3: Find remaining tag IDs (tags that still have mappings for this session)
      const remainingMappings = await db.select({
        tagId: breTagMapStaging.tagId
      })
      .from(breTagMapStaging)
      .where(eq(breTagMapStaging.sessionId, sessionId))

      const remainingTagIdSet = new Set(remainingMappings.map((m: any) => m.tagId))

      // Step 4: Delete orphaned tags (tags that no longer have any mappings)
      for (const tagId of tagIdsToDelete) {
        if (!remainingTagIdSet.has(tagId)) {
          await db.delete(breTagsStaging)
            .where(and(
              eq(breTagsStaging.sessionId, sessionId),
              eq(breTagsStaging.id, tagId)
            ))
          results.orphansCleaned++
        }
      }

      results.tagsDeleted = tagIdsToDelete.size
    } catch (error: any) {
      results.errors.push(`Tag deletion failed: ${error.message}`)
    }
  }

  // Process descriptions: delete descriptions for specified files
  if (type === 'descriptions' || type === 'both') {
    try {
      const deletedDescs = await db.delete(breDescriptionsStaging)
        .where(and(
          eq(breDescriptionsStaging.sessionId, sessionId),
          inArray(breDescriptionsStaging.fileId, file_ids)
        ))
      results.descriptionsDeleted = Number(deletedDescs) || 0
    } catch (error: any) {
      results.errors.push(`Description deletion failed: ${error.message}`)
    }
  }

  return {
    success: results.errors.length === 0,
    ...results
  }
})
