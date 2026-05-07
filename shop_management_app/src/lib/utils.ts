import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

export function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.substring(0, maxLength) + '...'
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15)
}

/**
 * Transform a preview URL from the database into a usable Nextcloud preview URL.
 * The preview_url column contains a path with {prevsize} placeholder that gets
 * replaced with actual size parameters.
 *
 * @param previewUrl - The preview URL from the database (contains {prevsize} placeholder)
 * @param size - The desired size in pixels (e.g., 64 for thumbnails, 1080 for full preview)
 * @returns The transformed URL ready for use in an img tag, or null if previewUrl is null
 */
export function transformPreviewUrl(previewUrl: string | null, size: number): string | null {
  if (!previewUrl) return null
  const ncHost = import.meta.env.NUXT_NC_HOST || 'localhost'
  const transformed = previewUrl.replace('{prevsize}', `x=${size}&y=${size}`)
  return `http://${ncHost}:8080${transformed}`
}
