// Gallery Composable
// Provides gallery CRUD operations and state management

export interface GalleryImage {
  id: number
  galleryId: number
  fileId: number
  displayOrder: number
  caption: string | null
  addedById: number
  addedAt: string
  fileName?: string
  previewUrl?: string
}

export interface GalleryAccessEntry {
  galleryId: number
  guestUserId: number
  grantedById: number
  grantedAt: string
  guestName?: string
  guestDisplayname?: string
  grantedByName?: string
}

export interface Gallery {
  id: number
  name: string
  description: string | null
  createdById: number
  updatedById: number | null
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface GalleryDetail extends Gallery {
  images: GalleryImage[]
  access: GalleryAccessEntry[]
}

export function useGalleries() {
  const galleries = ref<Gallery[]>([])
  const currentGallery = ref<GalleryDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const searchQuery = ref('')

  // Filtered galleries based on search
  const filteredGalleries = computed(() => {
    if (!searchQuery.value) return galleries.value
    const query = searchQuery.value.toLowerCase()
    return galleries.value.filter(g => 
      g.name.toLowerCase().includes(query) || 
      g.description?.toLowerCase().includes(query)
    )
  })

  // Fetch all galleries (filtered by user role)
  async function fetchGalleries(): Promise<Gallery[]> {
    loading.value = true
    error.value = null
    try {
      const response = await $fetch<Gallery[]>('/api/galleries')
      galleries.value = response
      return response
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch galleries'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Fetch single gallery with images and access list
  async function fetchGallery(id: number): Promise<GalleryDetail> {
    loading.value = true
    error.value = null
    try {
      const gallery = await $fetch<GalleryDetail>(`/api/galleries/${id}`)
      currentGallery.value = gallery
      
      // Also update in the list
      const index = galleries.value.findIndex((g: Gallery) => g.id === id)
      if (index !== -1) {
        galleries.value[index] = gallery
      }
      
      return gallery
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch gallery'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Create a new gallery
  async function createGallery(name: string, description?: string): Promise<Gallery> {
    loading.value = true
    error.value = null
    try {
      const gallery = await $fetch<Gallery>('/api/galleries', {
        method: 'POST',
        body: { name, description },
      })
      galleries.value.push(gallery)
      return gallery
    } catch (e: any) {
      error.value = e.message || 'Failed to create gallery'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Update gallery
  async function updateGallery(id: number, data: Partial<Pick<Gallery, 'name' | 'description' | 'isActive'>>): Promise<Gallery> {
    loading.value = true
    error.value = null
    try {
      const gallery = await $fetch<Gallery>(`/api/galleries/${id}`, {
        method: 'PUT',
        body: data,
      })
      // Update in list
      const index = galleries.value.findIndex((g: Gallery) => g.id === id)
      if (index !== -1) {
        galleries.value[index] = gallery
      }
      // Update current if same
      if (currentGallery.value?.id === id) {
        currentGallery.value = { ...currentGallery.value, ...gallery }
      }
      return gallery
    } catch (e: any) {
      error.value = e.message || 'Failed to update gallery'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Delete gallery
  async function deleteGallery(id: number): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await $fetch(`/api/galleries/${id}`, {
        method: 'DELETE',
      })
      galleries.value = galleries.value.filter((g: Gallery) => g.id !== id)
      if (currentGallery.value?.id === id) {
        currentGallery.value = null
      }
    } catch (e: any) {
      error.value = e.message || 'Failed to delete gallery'
      throw e
    } finally {
      loading.value = false
    }
  }

  // Toggle gallery active status
  async function toggleGalleryStatus(id: number): Promise<Gallery> {
    const gallery = galleries.value.find((g: Gallery) => g.id === id)
    if (!gallery) throw new Error('Gallery not found')
    return updateGallery(id, { isActive: !gallery.isActive })
  }

  // Reset state
  function reset() {
    galleries.value = []
    currentGallery.value = null
    error.value = null
  }

  return {
    galleries: computed(() => filteredGalleries.value),
    filteredGalleries,
    searchQuery,
    currentGallery,
    loading,
    error,
    fetchGalleries,
    fetchGallery,
    createGallery,
    updateGallery,
    deleteGallery,
    toggleGalleryStatus,
    reset,
  }
}
