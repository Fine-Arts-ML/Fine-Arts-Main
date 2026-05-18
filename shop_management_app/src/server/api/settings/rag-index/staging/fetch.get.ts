/**
 * Fetch Staged Data API
 * Retrieves all staged tags and descriptions for the current user's session.
 * Uses session-based isolation (session_id = userId from nuxt-auth-utils session).
 */
import { eq, inArray } from 'drizzle-orm'
import { breTagsStaging, breTagMapStaging, breDescriptionsStaging, ocFilecache } from '~/lib/nextcloud-schema'
import { getDb } from '~/lib/db'

export default defineEventHandler(async (event: any) => {
  // Authenticate user
  const session = await getUserSession(event)
  if (!session?.user?.id) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const sessionId = String(session.user.id)
  const db = getDb()

  // Get optional file_id filter
  const fileId = getQuery(event).file_id as string | undefined

  // Fetch all staged tags for this session
  const tags = await db.select()
    .from(breTagsStaging)
    .where(eq(breTagsStaging.sessionId, sessionId))
    .orderBy(breTagsStaging.name)

  // Fetch all staged tag mappings for this session
  let mappingsQuery = db.select()
    .from(breTagMapStaging)
    .where(eq(breTagMapStaging.sessionId, sessionId))

  // Fetch all staged descriptions for this session
  let descriptionsQuery = db.select()
    .from(breDescriptionsStaging)
    .where(eq(breDescriptionsStaging.sessionId, sessionId))

  // If file_id filter provided, filter mappings and descriptions
  if (fileId) {
    mappingsQuery = db.select()
      .from(breTagMapStaging)
      .where(eq(breTagMapStaging.sessionId, sessionId))
    descriptionsQuery = db.select()
      .from(breDescriptionsStaging)
      .where(eq(breDescriptionsStaging.sessionId, sessionId))
  }

  const mappings = await mappingsQuery
  const descriptions = await descriptionsQuery

  // Collect all unique file IDs
  const fileIds = new Set<string>()
  for (const mapping of mappings) {
    fileIds.add(String(mapping.fileId))
  }
  for (const desc of descriptions) {
    fileIds.add(String(desc.fileId))
  }

  // Fetch file metadata (names, paths) from oc_filecache for all file IDs
  // Note: oc_filecache has 'mimetype' (bigint ID), not 'mime_type' (string)
  // We'll determine image status from file extension instead
  const fileMetadataMap = new Map<string, { name: string; path: string }>()
  if (fileIds.size > 0) {
    const fileIdsArray = Array.from(fileIds).map(id => parseInt(id, 10))
    const fileCacheResults = await db.select({
      fileid: ocFilecache.fileid,
      name: ocFilecache.name,
      path: ocFilecache.path,
    })
      .from(ocFilecache)
      .where(inArray(ocFilecache.fileid, fileIdsArray))

    for (const fc of fileCacheResults) {
      fileMetadataMap.set(String(fc.fileid), {
        name: fc.name || '',
        path: fc.path || ''
      })
    }
  }

  // Group tags by file_id via mappings
  const tagsByFile: Record<string, Array<{ id: number; name: string }>> = {}
  for (const mapping of mappings) {
    const fileIdStr = String(mapping.fileId)
    if (!tagsByFile[fileIdStr]) {
      tagsByFile[fileIdStr] = []
    }
    const tag = tags.find((t: any) => t.id === mapping.tagId)
    if (tag) {
      tagsByFile[fileIdStr].push({
        id: tag.id,
        name: tag.name
      })
    }
  }

  // Group descriptions by file_id
  const descriptionsByFile: Record<string, Array<{ id: number; description: string; createdAt: string }>> = {}
  for (const desc of descriptions) {
    const fileIdStr = String(desc.fileId)
    if (!descriptionsByFile[fileIdStr]) {
      descriptionsByFile[fileIdStr] = []
    }
    descriptionsByFile[fileIdStr].push({
      id: desc.id,
      description: desc.description,
      createdAt: desc.createdAt?.toISOString() || new Date().toISOString()
    })
  }

  // Build file metadata lookup: fileId -> { fileName, filePath }
  const fileMetadata: Record<string, { fileName: string; filePath: string }> = {}
  for (const fileIdStr of fileIds) {
    const meta = fileMetadataMap.get(fileIdStr)
    if (meta) {
      // Extract the filename from the path (last segment)
      const pathParts = meta.path.split('/')
      const fileName = pathParts[pathParts.length - 1] || meta.name
      fileMetadata[fileIdStr] = {
        fileName,
        filePath: meta.path
      }
    } else {
      // Fallback: use file ID as filename
      fileMetadata[fileIdStr] = {
        fileName: fileIdStr,
        filePath: fileIdStr
      }
    }
  }

  return {
    success: true,
    tagsByFile,
    descriptionsByFile,
    fileMetadata,
    summary: {
      totalFilesWithTags: Object.keys(tagsByFile).length,
      totalFilesWithDescriptions: Object.keys(descriptionsByFile).length,
      totalStagedTags: tags.length,
      totalStagedDescriptions: descriptions.length
    }
  }
})
