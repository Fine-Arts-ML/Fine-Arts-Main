/**
 * Push Staged Data to Production API
 * Moves staged tags and descriptions to production tables.
 * Uses session-based isolation (session_id = userId from nuxt-auth-utils session).
 *
 * For tags: Inserts/updates in oc_systemtag and oc_systemtag_object_mapping.
 * For descriptions: Inserts into bre_descriptions with max 3 per file enforcement via trigger.
 * After successful push, clears staged data for pushed files.
 *
 * All operations are wrapped in a transaction for atomicity.
 */
import { eq, and, inArray } from 'drizzle-orm'
import { breTagsStaging, breTagMapStaging, breDescriptionsStaging, breDescriptions, ocSystemtag, ocSystemtagObjectMapping } from '~/lib/nextcloud-schema'
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
    file_ids?: string[]  // If empty/null, push all staged files
    type: 'tags' | 'descriptions' | 'both'
  } = body || {}

  if (!type || !['tags', 'descriptions', 'both'].includes(type)) {
    throw createError({ statusCode: 400, statusMessage: 'type must be tags, descriptions, or both' })
  }

  // Get all unique file_ids from staging for this session
  const allMappings = await db.select({ fileId: breTagMapStaging.fileId })
    .from(breTagMapStaging)
    .where(eq(breTagMapStaging.sessionId, sessionId))

  const allDescs = await db.select({ fileId: breDescriptionsStaging.fileId })
    .from(breDescriptionsStaging)
    .where(eq(breDescriptionsStaging.sessionId, sessionId))

  const allFileIdsSet = new Set<string>()
  for (const m of allMappings) {
    if (type === 'tags' || type === 'both') {
      allFileIdsSet.add(m.fileId)
    }
  }
  for (const d of allDescs) {
    if (type === 'descriptions' || type === 'both') {
      allFileIdsSet.add(d.fileId)
    }
  }

  let targetFileIds = Array.from(allFileIdsSet)

  // Filter to specific file_ids if provided
  if (file_ids && file_ids.length > 0) {
    targetFileIds = targetFileIds.filter(f => file_ids.includes(f))
  }

  // Wrap all operations in a transaction for atomicity
  const results = {
    tagsPushed: 0,
    descriptionsPushed: 0,
    errors: [] as string[]
  }

  try {
    await db.transaction(async (tx) => {
      // Process tags
      if (type === 'tags' || type === 'both') {
        for (const fileId of targetFileIds) {
          // Get all tags for this file
          const fileMappings = await tx.select({
            tagId: breTagMapStaging.tagId,
            tagName: breTagsStaging.name
          })
          .from(breTagMapStaging)
          .leftJoin(breTagsStaging, eq(breTagMapStaging.tagId, breTagsStaging.id))
          .where(and(
            eq(breTagMapStaging.sessionId, sessionId),
            eq(breTagMapStaging.fileId, fileId)
          ))

          for (const mapping of fileMappings) {
            if (!mapping.tagName) continue

            // Check oc_systemtag for existing tag by name (deduplication)
            const existingTag = await tx.select({ id: ocSystemtag.id })
              .from(ocSystemtag)
              .where(eq(ocSystemtag.name, mapping.tagName))
              .limit(1)

            let systemTagId: number

            if (existingTag.length > 0) {
              // Tag exists - reuse existing ID
              systemTagId = Number(existingTag[0].id)
            } else {
              // Tag does not exist - insert new tag (no color, managed by Nextcloud)
              const inserted = await tx.insert(ocSystemtag)
                .values({
                  name: mapping.tagName,
                  visibility: 1,
                  editable: 1
                })
                .returning({ id: ocSystemtag.id })
              systemTagId = Number(inserted[0].id)
            }

            // Insert into production oc_systemtag_object_mapping (use 'files' for Nextcloud compatibility)
            const existingMapping = await tx.select()
              .from(ocSystemtagObjectMapping)
              .where(and(
                eq(ocSystemtagObjectMapping.systemtagid, systemTagId),
                eq(ocSystemtagObjectMapping.objectid, fileId)
              ))
              .limit(1)

            if (existingMapping.length === 0) {
              await tx.insert(ocSystemtagObjectMapping).values({
                systemtagid: systemTagId,
                objectid: fileId,
                objecttype: 'files'
              })
            }

            results.tagsPushed += 1
          }
        }
      }

      // Process descriptions
      if (type === 'descriptions' || type === 'both') {
        for (const fileId of targetFileIds) {
          // Get staged description for this file
          const stagedDescs = await tx.select()
            .from(breDescriptionsStaging)
            .where(and(
              eq(breDescriptionsStaging.sessionId, sessionId),
              eq(breDescriptionsStaging.fileId, fileId)
            ))

          for (const staged of stagedDescs) {
            // Insert into production (trigger enforces max 3)
            await tx.insert(breDescriptions).values({
              fileId: staged.fileId,
              description: staged.description,
              pinned: false
            })
            results.descriptionsPushed += 1
          }
        }
      }

      // Clear staged data for pushed files
      if (targetFileIds.length > 0) {
        if (type === 'tags' || type === 'both') {
          await tx.delete(breTagMapStaging)
            .where(and(
              eq(breTagMapStaging.sessionId, sessionId),
              inArray(breTagMapStaging.fileId, targetFileIds)
            ))
        }

        if (type === 'descriptions' || type === 'both') {
          await tx.delete(breDescriptionsStaging)
            .where(and(
              eq(breDescriptionsStaging.sessionId, sessionId),
              inArray(breDescriptionsStaging.fileId, targetFileIds)
            ))
        }

        // Clean up orphaned tags (tags with no mappings for this session)
        const mappedTagIds = await tx.select({ tagId: breTagMapStaging.tagId })
          .from(breTagMapStaging)
          .where(eq(breTagMapStaging.sessionId, sessionId))

        const mappedTagIdSet = new Set(mappedTagIds.map((m: any) => m.tagId))

        // Delete tags that are no longer mapped
        const allTags = await tx.select({ id: breTagsStaging.id })
          .from(breTagsStaging)
          .where(eq(breTagsStaging.sessionId, sessionId))

        for (const tag of allTags) {
          if (!mappedTagIdSet.has(tag.id)) {
            await tx.delete(breTagsStaging)
              .where(and(
                eq(breTagsStaging.sessionId, sessionId),
                eq(breTagsStaging.id, tag.id)
              ))
          }
        }
      }
    })
  } catch (error: any) {
    // Transaction failed — staging data is preserved
    results.errors.push(`Transaction failed: ${error.message}`)
  }

  return {
    success: results.errors.length === 0,
    ...results,
    filesProcessed: targetFileIds.length
  }
})
