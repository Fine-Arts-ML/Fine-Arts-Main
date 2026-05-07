/**
 * Server-side utility for transforming Nextcloud preview URLs.
 *
 * The preview_url column in bre_advance_index stores relative paths with a {prevsize} placeholder:
 *   /core/preview?fileId=2158&{prevsize}
 *
 * Since the Nextcloud preview endpoint requires authentication, we transform these
 * into local proxy URLs that handle Basic Auth server-side:
 *   /api/files/preview-proxy/{fileId}?x=64&y=64
 */

/**
 * Extract the fileId from a raw preview_url.
 * Expected format: /core/preview?fileId=2158&{prevsize}
 *
 * @param rawPreviewUrl - The raw preview_url from the database
 * @returns The fileId, or null if not found
 */
function extractFileId(rawPreviewUrl: string): string | null {
  const match = rawPreviewUrl.match(/fileId=(\d+)/)
  return match ? match[1] ?? null : null
}

/**
 * Transform a raw preview_url from the database into a local proxy URL.
 *
 * @param rawPreviewUrl - The raw preview_url from bre_advance_index (e.g., "/core/preview?fileId=2158&{prevsize}")
 * @param size - The dimension size in pixels (used for both x and y)
 * @returns The proxy URL, or null if rawPreviewUrl is null/empty or fileId cannot be extracted
 */
export function transformPreviewUrl(rawPreviewUrl: string | null, size: number = 64): string | null {
  if (!rawPreviewUrl || rawPreviewUrl.trim() === '') {
    return null
  }

  const fileId = extractFileId(rawPreviewUrl)
  if (!fileId) {
    console.warn('[transformPreviewUrl] Could not extract fileId from:', rawPreviewUrl)
    return null
  }
  
  return `/api/files/preview-proxy/${fileId}?x=${size}&y=${size}`
}

/**
 * Transform an array of objects that have a previewUrl property.
 * Useful for transforming query results in bulk.
 * 
 * @param items - Array of objects with previewUrl property
 * @param size - The dimension size in pixels
 * @returns The same array with previewUrl properties transformed
 */
export function transformPreviewUrls<T extends { previewUrl?: string | null }>(items: T[], size: number = 64): T[] {
  for (const item of items) {
    if (item.previewUrl) {
      item.previewUrl = transformPreviewUrl(item.previewUrl, size)
    }
  }
  return items
}
