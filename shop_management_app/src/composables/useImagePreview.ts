/**
 * Composable for managing universal image preview state.
 *
 * Provides centralized open/close/gallery navigation for the ImagePreviewModal component.
 * Can be used across any page to open image previews.
 */

import { reactive, onMounted, onUnmounted } from 'vue'

export interface PreviewImage {
  fileId: number
  filename: string
  previewUrl: string // Full URL for the enlarged image (1080px+)
}

export function useImagePreview() {
  const state = reactive({
    isOpen: false,
    currentImage: null as PreviewImage | null,
    images: [] as PreviewImage[],
  })

  function open(image: PreviewImage) {
    state.currentImage = image
    state.images = [image]
    state.isOpen = true
    document.body.style.overflow = 'hidden'
  }

  function openGallery(images: PreviewImage[], startIndex: number) {
    state.images = images
    state.currentImage = images[startIndex] || null
    state.isOpen = true
    document.body.style.overflow = 'hidden'
  }

  function close() {
    state.isOpen = false
    state.currentImage = null
    state.images = []
    document.body.style.overflow = ''
  }

  function navigate(direction: 'prev' | 'next') {
    if (!state.currentImage || state.images.length === 0) return
    const currentIndex = state.images.findIndex(
      img => img.fileId === state.currentImage!.fileId
    )
    let newIndex: number
    if (direction === 'prev') {
      newIndex = (currentIndex - 1 + state.images.length) % state.images.length
    } else {
      newIndex = (currentIndex + 1) % state.images.length
    }
    state.currentImage = state.images[newIndex] || null
  }

  // Keyboard handler
  function handleKeyDown(event: KeyboardEvent) {
    if (!state.isOpen) return
    if (event.key === 'Escape') close()
    if (event.key === 'ArrowLeft') navigate('prev')
    if (event.key === 'ArrowRight') navigate('next')
  }

  // Register/unregister keyboard listener
  onMounted(() => window.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))

  return { state, open, openGallery, close, navigate }
}
