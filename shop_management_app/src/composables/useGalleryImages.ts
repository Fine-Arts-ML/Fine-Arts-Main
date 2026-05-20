// Gallery Images Composable
// Provides image management operations for a specific gallery
import type { GalleryImage, GalleryAccessEntry } from './useGalleries'

export function useGalleryImages(galleryId: Ref<number>) {
  const images = ref<GalleryImage[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Fetch all images in a gallery (ordered)
  async function fetchImages(): Promise<GalleryImage[]> {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<GalleryImage[]>(`/api/galleries/${galleryId.value}/images`)
      images.value = response
      return response
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch gallery images'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Add image(s) to gallery
  async function addImages(fileIds: number[], caption?: string): Promise<GalleryImage[]> {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<GalleryImage[]>(`/api/galleries/${galleryId.value}/images`, {
        method: 'POST',
        body: { fileIds, caption },
      })
      images.value.push(...response)
      return response
    } catch (e: any) {
      error.value = e.message || 'Failed to add images'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Bulk add images
  async function bulkAddImages(fileIds: number[]): Promise<GalleryImage[]> {
    return addImages(fileIds)
  }

  // Remove image from gallery
  async function removeImage(imageId: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await $fetch(`/api/galleries/${galleryId.value}/images/${imageId}`, {
        method: 'DELETE',
      })
      images.value = images.value.filter((img: GalleryImage) => img.id !== imageId)
    } catch (e: any) {
      error.value = e.message || 'Failed to remove image'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Reorder images
  async function reorderImages(order: number[]): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await $fetch(`/api/galleries/${galleryId.value}/images/reorder`, {
        method: 'POST',
        body: { order },
      })
      await fetchImages() // Refresh to get updated order
    } catch (e: any) {
      error.value = e.message || 'Failed to reorder images'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Update image caption
  async function updateCaption(imageId: number, caption: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await $fetch(`/api/galleries/${galleryId.value}/images/${imageId}`, {
        method: 'PUT',
        body: { caption },
      })
      const image = images.value.find((img: GalleryImage) => img.id === imageId)
      if (image) {
        image.caption = caption
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to update caption'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Transfer image(s) to another gallery
  async function transferImages(imageIds: number[], targetGalleryId: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      // First, get the file_ids of the images to transfer
      const imagesToTransfer = images.value.filter((img: GalleryImage) => imageIds.includes(img.id))
      const fileIds = imagesToTransfer.map((img: GalleryImage) => img.fileId)
      
      // Add to target gallery
      await $fetch(`/api/galleries/${targetGalleryId}/images`, {
        method: 'POST',
        body: { fileIds },
      })
      
      // Remove from current gallery
      for (const imageId of imageIds) {
        await removeImage(imageId)
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to transfer images'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    images,
    loading,
    error,
    fetchImages,
    addImages,
    bulkAddImages,
    removeImage,
    reorderImages,
    updateCaption,
    transferImages,
  }
}
