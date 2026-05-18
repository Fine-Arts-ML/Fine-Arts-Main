/**
 * Scan Directory API
 *
 * Native TypeScript implementation using pg pool and Drizzle ORM.
 * Scans directory for image files and returns their tag status.
 *
 * Converts frontend paths (e.g., /Tom/Bre/Artwork) to Nextcloud internal paths
 * (e.g., files/Bre/Artwork) using the userId and storageId parameters.
 */

import { scanDirectory } from '~/server/utils/directoryScanner'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const path = query.path as string
  const userId = (query.userId as string) || 'Tom'
  const storageId = query.storageId ? parseInt(query.storageId as string, 10) : undefined

  if (!path) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: path',
    })
  }

  // Parse file extensions if provided (comma-separated)
  let extensions: string[] | undefined
  if (query.file_extensions) {
    const extStr = query.file_extensions as string
    extensions = extStr.split(',').map(e => `.${e.trim().toLowerCase()}`)
  }

  try {
    const result = await scanDirectory(path, extensions, userId, storageId)
    return {
      success: true,
      data: result,
    }
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: error.message || 'Failed to scan directory',
      data: { error: error instanceof Error ? error.message : 'Unknown error' },
    })
  }
})
