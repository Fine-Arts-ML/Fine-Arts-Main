// Gallery Type Definitions

export interface Gallery {
  id: number
  name: string
  description: string | null
  createdById: number
  updatedById: number | null
  isActive: boolean
  createdAt: string | Date
  updatedAt: string | Date
}

export interface NewGallery {
  name: string
  description?: string
  createdById: number
}

export interface GalleryUpdate {
  name?: string
  description?: string
  isActive?: boolean
}

export interface GalleryImage {
  id: number
  galleryId: number
  fileId: number  // bigint from oc_filecache.fileid
  displayOrder: number
  caption: string | null
  addedById: number
  addedAt: string | Date
  // Joined data from oc_filecache
  fileName?: string
  path?: string
  previewUrl?: string
}

export interface NewGalleryImage {
  galleryId: number
  fileId: number
  displayOrder?: number
  caption?: string
  addedById: number
}

export interface GalleryAccessEntry {
  galleryId: number
  guestUserId: number
  grantedById: number
  grantedAt: string | Date
  // Joined data
  guestName?: string
  guestDisplayname?: string
  grantedByName?: string
}

export interface NewGalleryAccess {
  galleryId: number
  guestUserId: number
  grantedById: number
}

export interface GalleryWithImages extends Gallery {
  images: GalleryImage[]
  accessCount?: number
}

export interface GalleryListResponse {
  galleries: Gallery[]
  total: number
}

export interface GalleryDetailResponse extends Gallery {
  images: GalleryImage[]
  access: GalleryAccessEntry[]
}
