<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ChevronLeft,
  ChevronRight,
  X,
  Image as ImageIcon,
  Loader2,
  ArrowLeft,
} from 'lucide-vue-next'

// Route param
const route = useRoute()
const galleryId = computed(() => parseInt(route.params.id as string, 10))

// Gallery data
const gallery = ref<any>(null)
const images = ref<any[]>([])
const currentImageIndex = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

// Modal state
const showModal = ref(false)
const showLargePreview = ref(false)

// Preview URL helper
function getPreviewUrl(fileId: number, size: number = 512): string {
  return `/api/files/preview-proxy/${fileId}?size=${size}`
}

function getLargePreviewUrl(fileId: number): string {
  return `/api/files/preview-proxy/${fileId}?size=1080`
}

// Current image
const currentImage = computed(() => {
  if (images.value.length === 0) return null
  return images.value[currentImageIndex.value]
})

// Navigate to previous image
function prevImage() {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

// Navigate to next image
function nextImage() {
  if (currentImageIndex.value < images.value.length - 1) {
    currentImageIndex.value++
  }
}

// Open modal for specific image
function openImage(index: number) {
  currentImageIndex.value = index
  showModal.value = true
}

// Close modal
function closeModal() {
  showModal.value = false
}

// Open large preview
function openLargePreview() {
  showLargePreview.value = true
}

// Close large preview
function closeLargePreview() {
  showLargePreview.value = false
}

// Keyboard navigation
function handleKeydown(e: KeyboardEvent) {
  if (!showModal.value) return
  
  switch (e.key) {
    case 'ArrowLeft':
      prevImage()
      break
    case 'ArrowRight':
      nextImage()
      break
    case 'Escape':
      closeModal()
      break
  }
}

// Fetch gallery data
async function fetchGallery() {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch(`/api/galleries/${galleryId.value}`)
    gallery.value = data
    images.value = data.images || []
  } catch (e: any) {
    error.value = e.message || 'Failed to load gallery'
  } finally {
    loading.value = false
  }
}

// Watch for route changes
watch(() => galleryId.value, () => {
  if (galleryId.value) {
    fetchGallery()
  }
})

// Lifecycle
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  if (galleryId.value) {
    fetchGallery()
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// Format date
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}
</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Header -->
    <div class="border-b bg-card/50 backdrop-blur">
      <div class="px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <NuxtLink to="/galleries" class="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
              <ArrowLeft class="w-4 h-4" />
              <span>Back to Galleries</span>
            </NuxtLink>
            <div class="h-6 w-px bg-border" />
            <div>
              <h1 class="text-xl font-semibold">{{ gallery?.name || 'Loading...' }}</h1>
              <p v-if="gallery" class="text-sm text-muted-foreground">
                {{ images.length }} images • {{ formatDate(gallery.createdAt) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="mx-6 mt-4 p-4 bg-destructive/10 border border-destructive rounded-lg">
      <p class="text-destructive">{{ error }}</p>
    </div>

    <!-- Main Content -->
    <div class="p-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <Loader2 class="w-8 h-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Empty State -->
      <div v-else-if="!loading && images.length === 0" class="text-center py-20 text-muted-foreground">
        <ImageIcon class="w-16 h-16 mx-auto mb-4 opacity-50" />
        <p class="text-lg font-medium">No images yet</p>
        <p class="text-sm mt-1">This gallery is empty.</p>
      </div>

      <!-- Card Grid View -->
      <div v-else class="max-w-6xl mx-auto">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div
            v-for="(image, index) in images"
            :key="image.id"
            class="group cursor-pointer rounded-xl overflow-hidden bg-card border shadow-sm hover:shadow-md transition-shadow"
            @click="openImage(index)"
          >
            <div class="aspect-square overflow-hidden">
              <img
                :src="getPreviewUrl(image.fileId, 512)"
                :alt="image.caption || image.fileName || ''"
                class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
              />
            </div>
            <div class="p-4">
              <h3 v-if="image.fileName" class="font-medium truncate text-sm">
                {{ image.fileName }}
              </h3>
              <p v-if="image.caption" class="text-sm text-muted-foreground mt-1 line-clamp-2">
                "{{ image.caption }}"
              </p>
              <p v-else class="text-sm text-muted-foreground mt-1 line-clamp-1">
                No description available
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Image Modal Overlay -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showModal" class="fixed inset-0 z-50 bg-black/80 flex items-center justify-center" @click="closeModal">
          <!-- Close button -->
          <button
            class="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            @click.stop="closeModal"
          >
            <X class="w-6 h-6" />
          </button>

          <!-- Content wrapper -->
          <div
            class="relative max-w-6xl max-h-full p-4 flex flex-col items-center"
            @click.stop
          >
            <!-- Navigation -->
            <div class="flex items-center justify-between w-full mb-4">
              <button
                class="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors disabled:opacity-50"
                :disabled="currentImageIndex === 0"
                @click.stop="prevImage"
              >
                <ChevronLeft class="w-6 h-6" />
              </button>
              
              <span class="text-white text-sm">
                {{ currentImageIndex + 1 }} / {{ images.length }}
              </span>

              <button
                class="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors disabled:opacity-50"
                :disabled="currentImageIndex === images.length - 1"
                @click.stop="nextImage"
              >
                <ChevronRight class="w-6 h-6" />
              </button>
            </div>

            <!-- Main Image -->
            <div class="relative flex-1 flex items-center justify-center w-full max-h-[70vh]">
              <img
                v-if="currentImage"
                :src="getLargePreviewUrl(currentImage.fileId)"
                :alt="currentImage.caption || currentImage.fileName || ''"
                class="max-w-full max-h-full object-contain rounded-lg"
                @click="openLargePreview"
              />
            </div>

            <!-- Image Info -->
            <div v-if="currentImage" class="mt-4 text-center text-white max-w-2xl">
              <h3 v-if="currentImage.fileName" class="font-medium">
                {{ currentImage.fileName }}
              </h3>
              <p v-if="currentImage.caption" class="text-sm text-white/80 mt-1">
                "{{ currentImage.caption }}"
              </p>
            </div>

            <!-- Thumbnails -->
            <div class="flex gap-2 mt-4 overflow-x-auto max-w-full pb-2 px-4">
              <button
                v-for="(image, index) in images"
                :key="image.id"
                class="flex-shrink-0 w-16 h-16 rounded-md overflow-hidden border-2 transition-colors"
                :class="index === currentImageIndex ? 'border-white' : 'border-transparent'"
                @click.stop="currentImageIndex = index"
              >
                <img
                  :src="getPreviewUrl(image.fileId, 100)"
                  alt=""
                  class="w-full h-full object-cover"
                />
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Large Preview Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showLargePreview" class="fixed inset-0 z-[60] bg-black/95 flex items-center justify-center" @click="closeLargePreview">
          <button
            class="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
            @click.stop="closeLargePreview"
          >
            <X class="w-6 h-6" />
          </button>

          <div class="relative max-w-7xl max-h-full p-4 flex flex-col items-center" @click.stop>
            <img
              v-if="currentImage"
              :src="getLargePreviewUrl(currentImage.fileId)"
              :alt="currentImage.caption || currentImage.fileName || ''"
              class="max-w-full max-h-[90vh] object-contain rounded-lg"
            />
            
            <div v-if="currentImage" class="mt-4 text-center text-white max-w-2xl">
              <h3 class="font-medium">{{ currentImage.fileName }}</h3>
              <p v-if="currentImage.caption" class="text-sm text-white/80 mt-1">
                "{{ currentImage.caption }}"
              </p>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
