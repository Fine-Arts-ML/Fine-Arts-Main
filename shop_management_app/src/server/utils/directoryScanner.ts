/**
 * Directory Scanner Utility
 * 
 * Native TypeScript implementation for browsing and scanning Nextcloud directories.
 * Replaces the Python file_scanner.py microservice.
 * 
 * Uses pg pool directly for queries on Nextcloud tables with unmapped columns,
 * and Drizzle ORM for standard operations on mapped tables.
 */

import { Pool } from 'pg'
import {
  ocSystemtag,
  ocSystemtagObjectMapping,
  ocFilecache,
} from '~/lib/nextcloud-schema'
import { eq, and, asc, inArray } from 'drizzle-orm'
import { getDb } from '~/lib/db'

// ========== Type Definitions (TagInfo defined locally) ==========

export interface TagInfo {
  id: number
  name: string
  color: string
}

// ========== Type Definitions ==========

export interface DbItem {
  fileid: number
  name: string
  mime_type: string
  size: number
  mtime: number
  is_directory: boolean
}

export interface FileInfo {
  file_id: string
  file_name: string
  file_path: string
  file_size: number
  mime_type: string
  last_modified: string | null
  is_directory: boolean
  existing_tags: TagInfo[]
  is_tagged: boolean
}

export interface DirectoryListing {
  path: string
  items: FileInfo[]
  total_files: number
  total_directories: number
  tagged_count: number
  untagged_count: number
}

export interface ScanResult {
  path: string
  files: FileInfo[]
  total_files: number
  tagged_count: number
  untagged_count: number
}

export interface Breadcrumb {
  path: string
  label: string
}

// ========== Default Image Extensions ==========

const DEFAULT_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']

// ========== MIME Type Helpers ==========

const IMAGE_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/bmp',
  'image/tiff',
  'image/webp',
  'image/svg+xml',
])

/**
 * Check if a MIME type is an image
 */
export function isImageMimeType(mimeType: string): boolean {
  return IMAGE_MIME_TYPES.has(mimeType)
}

/**
 * Get file extension in lowercase
 */
function getFileExtension(fileName: string): string {
  const lastDot = fileName.lastIndexOf('.')
  if (lastDot === -1) return ''
  return fileName.substring(lastDot).toLowerCase()
}

/**
 * Normalize directory path (ensure leading slash, no trailing slash)
 */
function normalizePath(path: string): string {
  path = path.trim()
  if (!path || path === '/') return '/'
  return path.endsWith('/') ? path.slice(0, -1) : path
}

/**
 * Get the WebDAV base path for a user
 * Default user is "Tom" as per Nextcloud configuration
 */
function getWebDavBasePath(username: string = 'Tom'): string {
  return `/${username}`
}

/**
 * Convert frontend path to Nextcloud internal path
 *
 * Frontend paths: /Tom/Bre/Artwork, /Wop/Shops, etc.
 * Internal paths: files/Bre/Artwork, files/Shops, etc.
 *
 * The conversion strips the leading /{userId} and replaces it with 'files'.
 * This works because all user storages use the same 'files/' prefix structure.
 *
 * @param frontendPath - Path from frontend (e.g., /Tom/Bre/Artwork)
 * @param storageId - Nextcloud storage numeric_id (e.g., 1 for Tom, 3 for Wop)
 * @returns Internal path (e.g., files/Bre/Artwork) or null if conversion fails
 */
function convertToFrontendPath(frontendPath: string, storageId?: number): string | null {
  const normalized = normalizePath(frontendPath)
  
  if (!normalized || normalized === '/') {
    return 'files'
  }
  
  // If path already starts with 'files/', return as-is
  if (normalized.startsWith('/files') || normalized === 'files') {
    return normalized.startsWith('/') ? normalized.slice(1) : normalized
  }
  
  // Extract userId from path (e.g., /Tom/Bre/Artwork -> Tom)
  // Also check storageId parameter to validate
  const parts = normalized.split('/').filter(Boolean)
  if (parts.length === 0) {
    return 'files'
  }
  
  const userId = parts[0]
  const subPath = parts.slice(1).join('/')
  
  // Build internal path: files/{subPath}
  const internalPath = subPath ? `files/${subPath}` : 'files'
  
  return internalPath
}

// ========== PostgreSQL Pool for Raw Queries ==========

/**
 * Create a pg Pool for raw SQL queries
 * Nextcloud tables have columns not mapped in Drizzle (like is_dir),
 * so we use raw SQL for those operations.
 */
function createDbPool(): Pool {
  const dbHost = process.env.DB_HOST || 'localhost'
  const dbPort = Number(process.env.DB_PORT) || 5432
  const dbName = process.env.DB_NAME || 'nextpsql'
  const dbUser = process.env.DB_USER || 'nextuser'
  const dbPassword = process.env.DB_PASSWORD || ''

  return new Pool({
    host: dbHost,
    port: dbPort,
    database: dbName,
    user: dbUser,
    password: dbPassword,
  })
}

let pool: Pool | null = null

function getPool(): Pool {
  if (!pool) {
    pool = createDbPool()
  }
  return pool
}

// ========== Core Scanner Functions ==========

/**
 * List contents of a directory
 * Uses raw SQL to query oc_filecache including the is_dir column
 *
 * Accepts frontend paths (e.g., /Tom/Bre/Artwork) and converts them to
 * Nextcloud internal paths (e.g., files/Bre/Artwork) for database queries.
 * Uses storageId to query the correct user's files.
 */
export async function listDirectory(
  path: string,
  username: string = 'Tom',
  storageId?: number
): Promise<DirectoryListing> {
  const db = getDb()
  
  // Convert frontend path to Nextcloud internal path
  const internalPath = convertToFrontendPath(path, storageId)
  
  console.log('[listDirectory] Input path:', path, 'username:', username, 'storageId:', storageId, 'internalPath:', internalPath)
  
  if (!internalPath) {
    return {
      path: normalizePath(path),
      items: [],
      total_files: 0,
      total_directories: 0,
      tagged_count: 0,
      untagged_count: 0,
    }
  }
  
  // Determine the storage to query
  // If storageId is provided, use it. Otherwise, look up by username.
  let storageFilter: string | number
  if (storageId) {
    storageFilter = storageId
  } else {
    // Fallback: look up storage by username
    const pg = getPool()
    const storageResult = await pg.query<Record<string, any>>(
      'SELECT numeric_id FROM oc_storages WHERE id = $1',
      [`home::${username}`]
    )
    if (storageResult.rows.length === 0) {
      throw new Error(`Storage not found for user: ${username}`)
    }
    storageFilter = parseInt(storageResult.rows[0].numeric_id, 10)
  }

  try {
    // First, get the parent directory's fileid using raw SQL with storage filter
    const pg = getPool()
    const parentResult = await pg.query<Record<string, any>>(
      `SELECT fileid FROM oc_filecache
       WHERE storage = $1 AND path = $2`,
      [storageFilter, internalPath]
    )

    if (parentResult.rows.length === 0) {
      // Directory not found, return empty listing
      return {
        path: internalPath,
        items: [],
        total_files: 0,
        total_directories: 0,
        tagged_count: 0,
        untagged_count: 0,
      }
    }

    const parentFileId = Number(parentResult.rows[0].fileid)

    // Use raw SQL to get items with JOIN to oc_mimetypes to resolve MIME types
    // Note: oc_filecache stores mimetype as bigint ID referencing oc_mimetypes.id
    // There is no 'mime_type' or 'is_dir' column in oc_filecache
    const itemsResult = await pg.query<Record<string, any>>(
      `SELECT
        fc.fileid,
        fc.name,
        mt.mimetype AS mime_type,
        COALESCE(fc.size, 0) as size,
        COALESCE(fc.mtime, 0) as mtime,
        CASE WHEN mt.mimetype = 'httpd/unix-directory' THEN true ELSE false END as is_directory
      FROM oc_filecache fc
      LEFT JOIN oc_mimetypes mt ON fc.mimetype = mt.id
      WHERE fc.parent = $1
      ORDER BY CASE WHEN mt.mimetype = 'httpd/unix-directory' THEN 0 ELSE 1 END, fc.name ASC`,
      [parentFileId]
    )

    // Type cast the results
    const items: DbItem[] = itemsResult.rows.map(row => ({
      fileid: Number(row.fileid),
      name: row.name || '',
      mime_type: row.mime_type || '',
      size: Number(row.size) || 0,
      mtime: Number(row.mtime) || 0,
      is_directory: row.is_directory === true || row.is_directory === 'true',
    }))

    // Collect all file IDs for tag lookup
    const fileIds = items
      .filter((item: DbItem) => !item.is_directory)
      .map((item: DbItem) => item.fileid.toString())

    // Get all tags for all files in one query using Drizzle
    const tagsByFile = new Map<string, TagInfo[]>()
    if (fileIds.length > 0) {
      const tagResults = await db
        .select({
          objectid: ocSystemtagObjectMapping.objectid,
          tagId: ocSystemtag.id,
          tagName: ocSystemtag.name,
          tagColor: ocSystemtag.color,
        })
        .from(ocSystemtagObjectMapping)
        .innerJoin(
          ocSystemtag,
          eq(ocSystemtagObjectMapping.systemtagid, ocSystemtag.id)
        )
        .where(
          and(
            eq(ocSystemtagObjectMapping.objecttype, 'files'),
            inArray(ocSystemtagObjectMapping.objectid, fileIds)
          )
        )
        .orderBy(asc(ocSystemtag.name))

      for (const row of tagResults) {
        const existing = tagsByFile.get(row.objectid) || []
        existing.push({
          id: Number(row.tagId),
          name: row.tagName,
          color: row.tagColor || '',
        })
        tagsByFile.set(row.objectid, existing)
      }
    }

    // Build the listing
    const listing: DirectoryListing = {
      path: internalPath,
      items: [],
      total_files: 0,
      total_directories: 0,
      tagged_count: 0,
      untagged_count: 0,
    }

    for (const item of items) {
      const itemName = item.name || ''
      const itemPath = internalPath === 'files' ? `/files/${itemName}` : `${internalPath}/${itemName}`
      
      const fileInfo: FileInfo = {
        file_id: item.fileid.toString(),
        file_name: itemName,
        file_path: itemPath,
        file_size: item.size,
        mime_type: item.mime_type,
        last_modified: item.mtime ? new Date(item.mtime * 1000).toISOString() : null,
        is_directory: item.is_directory,
        existing_tags: tagsByFile.get(item.fileid.toString()) || [],
        is_tagged: false,
      }

      if (!item.is_directory) {
        fileInfo.is_tagged = fileInfo.existing_tags.length > 0
        if (fileInfo.is_tagged) {
          listing.tagged_count++
        } else {
          listing.untagged_count++
        }
        listing.total_files++
      } else {
        listing.total_directories++
      }

      listing.items.push(fileInfo)
    }

    return listing
  } catch (error) {
    console.error('[DirectoryScanner] Error listing directory:', error)
    throw new Error(`Failed to list directory: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Recursively scan a directory and its subdirectories for image files
 * Uses raw SQL to query all files under a path prefix in oc_filecache
 */
async function scanDirectoryRecursive(
  internalPath: string,
  storageId: number,
  extensions: string[],
  username: string
): Promise<{ files: FileInfo[]; tagged_count: number; untagged_count: number }> {
  const db = getDb()
  const pg = getPool()

  // Get all file IDs under this path (including subdirectories)
  // The path in oc_filecache is like 'files/Bre/Artwork'
  // We need to find all files where path starts with 'files/Bre/Artwork/'
  const pathPrefix = internalPath === 'files' ? 'files/' : `${internalPath}/`
  
  const allFilesResult = await pg.query<Record<string, any>>(
    `SELECT
      fc.fileid,
      fc.name,
      fc.path,
      mt.mimetype AS mime_type,
      COALESCE(fc.size, 0) as size,
      COALESCE(fc.mtime, 0) as mtime
    FROM oc_filecache fc
    LEFT JOIN oc_mimetypes mt ON fc.mimetype = mt.id
    WHERE fc.storage = $1
      AND fc.path LIKE $2
      AND mt.mimetype != 'httpd/unix-directory'`,
    [storageId, `${pathPrefix}%`]
  )

  // Filter to only image files with matching extensions
  const files: FileInfo[] = []
  let tagged_count = 0
  let untagged_count = 0

  // Collect all file IDs for tag lookup
  const fileIds = allFilesResult.rows
    .map(row => Number(row.fileid).toString())
  
  // Get all tags for all files in one query
  const tagsByFile = new Map<string, TagInfo[]>()
  if (fileIds.length > 0) {
    const tagResults = await db
      .select({
        objectid: ocSystemtagObjectMapping.objectid,
        tagId: ocSystemtag.id,
        tagName: ocSystemtag.name,
        tagColor: ocSystemtag.color,
      })
      .from(ocSystemtagObjectMapping)
      .innerJoin(
        ocSystemtag,
        eq(ocSystemtagObjectMapping.systemtagid, ocSystemtag.id)
      )
      .where(
        and(
          eq(ocSystemtagObjectMapping.objecttype, 'files'),
          inArray(ocSystemtagObjectMapping.objectid, fileIds)
        )
      )
      .orderBy(asc(ocSystemtag.name))

    for (const row of tagResults) {
      const existing = tagsByFile.get(row.objectid) || []
      existing.push({
        id: Number(row.tagId),
        name: row.tagName,
        color: row.tagColor || '',
      })
      tagsByFile.set(row.objectid, existing)
    }
  }

  // Build file info for each file
  for (const row of allFilesResult.rows) {
    const fileId = Number(row.fileid).toString()
    const ext = getFileExtension(row.name)
    
    // Check if file matches image criteria
    if (extensions.includes(ext) || isImageMimeType(row.mime_type)) {
      // Build the relative path from the database path
      // Database path: 'files/Bre/Artwork/Fine Arts/image.jpg'
      // We want: '/Tom/Bre/Artwork/Fine Arts/image.jpg'
      const relativePath = row.path.replace(/^files\//, '')
      const frontendPath = `/${username}/${relativePath}`
      
      const tags = tagsByFile.get(fileId) || []
      const is_tagged = tags.length > 0
      
      const fileInfo: FileInfo = {
        file_id: fileId,
        file_name: row.name,
        file_path: frontendPath,
        file_size: Number(row.size) || 0,
        mime_type: row.mime_type || '',
        last_modified: row.mtime ? new Date(Number(row.mtime) * 1000).toISOString() : null,
        is_directory: false,
        existing_tags: tags,
        is_tagged: is_tagged,
      }

      if (is_tagged) {
        tagged_count++
      } else {
        untagged_count++
      }
      
      files.push(fileInfo)
    }
  }

  return { files, tagged_count, untagged_count }
}

/**
 * Scan directory for image files (recursively)
 * Returns only image files with their tag status
 *
 * Accepts frontend paths (e.g., /Tom/Bre/Artwork) and converts them to
 * Nextcloud internal paths (e.g., files/Bre/Artwork) for database queries.
 * Uses storageId to query the correct user's files.
 */
export async function scanDirectory(
  path: string,
  extensions: string[] = DEFAULT_IMAGE_EXTENSIONS,
  username: string = 'Tom',
  storageId?: number
): Promise<ScanResult> {
  const db = getDb()
  
  // Convert frontend path to Nextcloud internal path
  const internalPath = convertToFrontendPath(path, storageId)
  
  if (!internalPath) {
    return {
      path: normalizePath(path),
      files: [],
      total_files: 0,
      tagged_count: 0,
      untagged_count: 0,
    }
  }

  // Determine the storage to query
  let storageFilter: number
  if (storageId) {
    storageFilter = storageId
  } else {
    // Fallback: look up storage by username
    const pg = getPool()
    const storageResult = await pg.query<Record<string, any>>(
      'SELECT numeric_id FROM oc_storages WHERE id = $1',
      [`home::${username}`]
    )
    if (storageResult.rows.length === 0) {
      throw new Error(`Storage not found for user: ${username}`)
    }
    storageFilter = parseInt(storageResult.rows[0].numeric_id, 10)
  }

  try {
    const result = await scanDirectoryRecursive(internalPath, storageFilter, extensions, username)
    
    return {
      path: normalizePath(path),
      files: result.files,
      total_files: result.files.length,
      tagged_count: result.tagged_count,
      untagged_count: result.untagged_count,
    }
  } catch (error) {
    console.error('[scanDirectory] Error:', error)
    throw new Error(`Failed to scan directory: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Get tag status for a specific file
 */
export async function getFileTagStatus(fileId: string): Promise<{
  file_id: string
  is_tagged: boolean
  tags: TagInfo[]
  tag_count: number
}> {
  const db = getDb()

  try {
    const tagResults = await db
      .select({
        id: ocSystemtag.id,
        name: ocSystemtag.name,
        color: ocSystemtag.color,
      })
      .from(ocSystemtagObjectMapping)
      .innerJoin(
        ocSystemtag,
        eq(ocSystemtagObjectMapping.systemtagid, ocSystemtag.id)
      )
      .where(
        and(
          eq(ocSystemtagObjectMapping.objecttype, 'files'),
          eq(ocSystemtagObjectMapping.objectid, fileId)
        )
      )
      .orderBy(asc(ocSystemtag.name))

    const tags: TagInfo[] = tagResults.map(row => ({
      id: Number(row.id),
      name: row.name,
      color: row.color || '',
    }))

    return {
      file_id: fileId,
      is_tagged: tags.length > 0,
      tags,
      tag_count: tags.length,
    }
  } catch (error) {
    console.error('[DirectoryScanner] Error getting file tag status:', error)
    throw new Error(`Failed to get tag status: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

/**
 * Generate breadcrumb trail for navigation
 */
export function getDirectoryBreadcrumbs(path: string, username: string = 'Tom'): Breadcrumb[] {
  const normalizedPath = normalizePath(path)
  const basePath = getWebDavBasePath(username)

  if (normalizedPath === '/' || normalizedPath === basePath) {
    return [{ path: '', label: 'Home' }]
  }

  const parts = normalizedPath.split('/').filter(Boolean)
  const breadcrumbs: Breadcrumb[] = [{ path: '', label: 'Home' }]

  let currentPath = ''
  for (const part of parts) {
    currentPath = `${currentPath}/${part}`
    breadcrumbs.push({
      path: currentPath,
      label: part,
    })
  }

  return breadcrumbs
}

/**
 * Check if a file exists in Nextcloud
 */
export async function checkFileExists(fileId: string): Promise<boolean> {
  const db = getDb()

  try {
    const fileIdNum = Number(fileId)
    const result = await db
      .select({ fileid: ocFilecache.fileid })
      .from(ocFilecache)
      .where(eq(ocFilecache.fileid, fileIdNum))
      .limit(1)

    return result.length > 0
  } catch (error) {
    console.error('[DirectoryScanner] Error checking file existence:', error)
    return false
  }
}

/**
 * Get preview URL for a file via Nextcloud WebDAV
 */
export function getFilePreviewUrl(fileId: string, webdavBaseUrl: string): string {
  const baseUrl = webdavBaseUrl.replace(/\/+$/, '')
  return `${baseUrl}/core/preview?fileId=${fileId}&x=1080&y=1080&a=false`
}

/**
 * Get all untagged image files in a directory
 */
export async function getUntaggedFiles(
  path: string,
  extensions: string[] = DEFAULT_IMAGE_EXTENSIONS,
  username: string = 'Tom'
): Promise<FileInfo[]> {
  const result = await scanDirectory(path, extensions, username)
  return result.files.filter(f => !f.is_tagged)
}

/**
 * Get all tagged image files in a directory
 */
export async function getTaggedFiles(
  path: string,
  extensions: string[] = DEFAULT_IMAGE_EXTENSIONS,
  username: string = 'Tom'
): Promise<FileInfo[]> {
  const result = await scanDirectory(path, extensions, username)
  return result.files.filter(f => f.is_tagged)
}
