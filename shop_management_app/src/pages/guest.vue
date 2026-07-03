<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '~/composables/useAuth'
import {
  GalleryVertical,
  EyeOff,
  Loader2,
  Image as ImageIcon,
  Users,
  AlertCircle,
} from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
})

useHead({
  title: 'Guest Portal - Art Management',
})

const router = useRouter()
const { user, isGuest } = useAuth()

// Gallery data
const galleries = ref<Array<{
  id: number
  name: string
  description: string | null
  imageCount: number
}>>([])
const loading = ref(true)
const error = ref<string | null>(null)

// Fetch accessible galleries for guest
async function fetchAccessibleGalleries() {
  loading.value = true
  error.value = null
  try {
    const data = await $fetch<Array<{
      id: number
      name: string
      description: string | null
      imageCount: number
    }>>('/api/galleries/my')
    galleries.value = data
  } catch (e: any) {
    error.value = e.message || 'Failed to fetch galleries'
  } finally {
    loading.value = false
  }
}

const galleryCount = computed(() => galleries.value.length)

// If guest has exactly one gallery, navigate to it
const shouldAutoNavigate = computed(() => galleryCount.value === 1)

onMounted(async () => {
  await fetchAccessibleGalleries()
  
  // Auto-navigate if only one gallery
  if (shouldAutoNavigate.value && galleries.value.length === 1) {
    router.push(`/gallery/${galleries.value[0].id}`)
  }
})

function navigateToGallery(id: number) {
  router.push(`/gallery/${id}`)
}
</script>

<template>
  <div class="p-6 max-w-6xl mx-auto">
    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-24">
      <Loader2 class="w-12 h-12 animate-spin text-blue-600 dark:text-blue-400" />
      <p class="mt-4 text-gray-600 dark:text-gray-400">Loading your galleries...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6">
      <div class="flex items-center gap-3">
        <AlertCircle class="w-6 h-6 text-red-500" />
        <div>
          <h3 class="font-medium text-red-800 dark:text-red-300">Error</h3>
          <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
        </div>
      </div>
    </div>

    <!-- No Galleries State -->
    <div v-else-if="galleryCount === 0" class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-12">
      <div class="flex flex-col items-center text-center">
        <div class="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mb-4">
          <EyeOff class="w-8 h-8 text-gray-400" />
        </div>
        <h2 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2">No Galleries Available</h2>
        <p class="text-sm text-gray-600 dark:text-gray-400 max-w-md">
          You don't have access to any galleries yet. Please contact the administrator to request access.
        </p>
      </div>
    </div>

    <!-- Gallery Selection -->
    <div v-else>
      <!-- Banner Header -->
      <div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-8 mb-6">
        <div class="flex items-start gap-4">
          <div class="w-12 h-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
            <GalleryVertical class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div class="flex-1">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Welcome back, {{ user?.displayName }}
            </h1>
            <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Select a gallery to view
              <span v-if="galleryCount > 1">({{ galleryCount }} galleries available)</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Gallery Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <button
          v-for="gallery in galleries"
          :key="gallery.id"
          @click="navigateToGallery(gallery.id)"
          class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 hover:border-blue-300 dark:hover:border-blue-700 transition-colors group"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1">
              <h3 class="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                {{ gallery.name }}
              </h3>
              <p v-if="gallery.description" class="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">
                {{ gallery.description }}
              </p>
            </div>
            <div class="flex items-center gap-1.5 ml-3">
              <ImageIcon class="w-4 h-4 text-gray-400" />
              <span class="text-xs font-medium text-gray-500 dark:text-gray-400">
                {{ gallery.imageCount ?? '?' }}
              </span>
            </div>
          </div>
          <div class="flex items-center justify-between mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
            <span class="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <Users class="w-3 h-3" />
              Guest Access
            </span>
            <span class="text-xs font-medium text-blue-600 dark:text-blue-400 group-hover:translate-x-1 transition-transform">
              View Gallery →
            </span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>
