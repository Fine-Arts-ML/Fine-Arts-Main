/**
 * Push Generated Data to Staging API
 * Pushes AI-generated tags and descriptions to staging tables for review before production.
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
  const { tags, descriptions }: {
    tags?: Record<string, string[]>  // { "fileId": ["tag1", "tag2"] }
    descriptions?: Record<string, string>  // { "fileId": "description text" }
  } = body || {}

  if (!tags && !descriptions) {
    throw createError({ statusCode: 400, statusMessage: 'No data to stage. Provide tags or descriptions.' })
  }

  const results = {
    tagsStaged: 0,
    descriptionsStaged: 0,
    tagErrors: [] as string[],
    descriptionErrors: [] as string[]
  }

  // Process tags
  if (tags && Object.keys(tags).length > 0) {
    for (const [fileId, tagNames] of Object.entries(tags)) {
      try {
        // Insert unique tags (upsert on session_id + name)
        for (const tagName of tagNames) {
          const existing = await db.select()
            .from(breTagsStaging)
            .where(and(
              eq(breTagsStaging.sessionId, sessionId),
              eq(breTagsStaging.name, tagName)
            ))
            .limit(1)

          let tagId: number

          if (existing.length > 0) {
            tagId = existing[0].id
          } else {
            const inserted = await db.insert(breTagsStaging)
              .values({
                sessionId,
                name: tagName
              })
              .returning({ id: breTagsStaging.id })
            tagId = inserted[0].id
          }

          // Insert tag-file mapping (skip if already exists)
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
        }
        results.tagsStaged += tagNames.length
      } catch (error: any) {
        results.tagErrors.push(`File ${fileId}: ${error.message}`)
      }
    }
  }

  // Process descriptions
  if (descriptions && Object.keys(descriptions).length > 0) {
    for (const [fileId, description] of Object.entries(descriptions)) {
      try {
        // Remove any existing staged description for this file
        await db.delete(breDescriptionsStaging)
          .where(and(
            eq(breDescriptionsStaging.sessionId, sessionId),
            eq(breDescriptionsStaging.fileId, fileId)
          ))

        // Insert new description
        await db.insert(breDescriptionsStaging).values({
          sessionId,
          fileId,
          description
        })
        results.descriptionsStaged += 1
      } catch (error: any) {
        results.descriptionErrors.push(`File ${fileId}: ${error.message}`)
      }
    }
  }

  return {
    success: results.tagErrors.length === 0 && results.descriptionErrors.length === 0,
    ...results
  }
})
