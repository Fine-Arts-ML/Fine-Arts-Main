// Gallery Access Composable
// Provides access management operations for a specific gallery
import type { GalleryAccessEntry } from './useGalleries'

export function useGalleryAccess(galleryId: Ref<number>) {
  const accessList = ref<GalleryAccessEntry[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Fetch access list for a gallery
  async function fetchAccess(): Promise<GalleryAccessEntry[]> {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<GalleryAccessEntry[]>(`/api/galleries/${galleryId.value}/access`)
      accessList.value = response
      return response
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch access list'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Grant access to a guest
  async function grantAccess(guestUserId: number): Promise<GalleryAccessEntry> {
    loading.value = true
    error.value = null
    try {
      // Get current user ID from session
      const user = useSessionStorage('user')
      const userId = user.value?.id

      const response = await $fetch<GalleryAccessEntry>(`/api/galleries/${galleryId.value}/access`, {
        method: 'POST',
        body: { guestUserId, grantedById: userId },
      })
      accessList.value.push(response)
      return response
    } catch (e: any) {
      error.value = e.message || 'Failed to grant access'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Revoke access from a guest
  async function revokeAccess(guestUserId: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await $fetch(`/api/galleries/${galleryId.value}/access/${guestUserId}`, {
        method: 'DELETE',
      })
      accessList.value = accessList.value.filter((entry: GalleryAccessEntry) => entry.guestUserId !== guestUserId)
    } catch (e: any) {
      error.value = e.message || 'Failed to revoke access'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    accessList,
    loading,
    error,
    fetchAccess,
    grantAccess,
    revokeAccess,
  }
}
