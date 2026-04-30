<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRagSearch, type SearchResult } from '~/composables/useRagSearch'
import { useLinkFiles } from '~/composables/useLinkFiles'
import { useImagePreview } from '~/composables/useImagePreview'
import type { LinkFileResult } from '~/types/linkFiles'
import { Search, FileImage, Loader2, AlertCircle } from 'lucide-vue-next'

// Image preview
const { open, close, navigate, state: previewState } = useImagePreview()

// RAG search state
const { search: ragSearch, clearResults: clearRagResults } = useRagSearch()
const ragResults = ref<SearchResult[]>([])
const ragQueryTimeMs = ref(0)

// Link files search state (for Name Search mode)
const {
  searchQuery,
  searchResults: linkFilesResults,
  searchLoading: linkFilesLoading,
  searchError,
  searchByFilename,
  clearResults: clearLinkFilesResults,
} = useLinkFiles()

// Available modes
type BrowseMode = 'semantic' | 'name' | 'browse_all' | 'by_shop' | 'by_acc'
const activeMode = ref<BrowseMode>('semantic')

const modes = [
  { value: 'semantic', label: 'Semantic Search' },
  { value: 'name', label: 'Name Search' },
  { value: 'browse_all', label: 'Browse all' },
  { value: 'by_shop', label: 'By Shop' },
  { value: 'by_acc', label: 'By Account' }
]

// Switch mode
function switchMode(mode: BrowseMode) {
  activeMode.value = mode
  // Clear results when switching modes
  ragResults.value = []
  ragQueryTimeMs.value = 0
  searchQuery.value = ''
}

// Perform semantic search
async function performSemanticSearch() {
  const query = searchQuery.value.trim()
  if (!query) {
    searchError.value = 'Please enter a search query'
    return
  }

  isLoading.value = true
  searchError.value = null
  ragResults.value = []
  ragQueryTimeMs.value = 0

  try {
    const response = await ragSearch(query, { top_k: 24 })
    ragResults.value = response.results
    ragQueryTimeMs.value = response.query_time_ms
  } catch (err: any) {
    searchError.value = err.message || 'Search failed. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Perform name search (using useLinkFiles)
function performNameSearch() {
  const query = searchQuery.value.trim()
  if (!query) {
    searchError.value = 'Please enter a search query'
    return
  }
  searchByFilename(query)
}

// Handle search input submit
function handleSearchSubmit() {
  if (activeMode.value === 'semantic') {
    performSemanticSearch()
  } else if (activeMode.value === 'name') {
    performNameSearch()
  }
}

function handleKeyup(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    handleSearchSubmit()
  }
}

// Clear all search state
function clearSearch() {
  searchQuery.value = ''
  ragResults.value = []
  ragQueryTimeMs.value = 0
  searchError.value = null
  clearRagResults()
  clearLinkFilesResults()
}

// Format similarity score for display
function formatSimilarity(score: number): string {
  return (score * 100).toFixed(1) + '%'
}

// Get preview URL for a file by fileId
function getPreviewUrl(fileId: number, size: number = 540): string {
  return `/api/files/preview-proxy/${fileId}?x=${size}&y=${size}`
}

// Get enlarged preview URL (1080px)
function getEnlargedPreviewUrl(fileId: number): string {
  return `/api/files/preview-proxy/${fileId}?x=1080&y=1080`
}

// Open image preview modal
function openPreview(fileId: number, filename: string) {
  open({ fileId, filename, previewUrl: getEnlargedPreviewUrl(fileId) })
}

// Get filename from result
function getFilename(result: SearchResult | LinkFileResult): string {
  return result.filename
}

// Get fileId from result
function getFileId(result: SearchResult | LinkFileResult): number {
  if ('file_id' in result) {
    return result.file_id as number
  }
  return result.fileId
}

// Check if result has similarity property (semantic search only)
function hasSimilarity(result: SearchResult | LinkFileResult): result is SearchResult {
  return 'similarity' in result
}

// Computed property for current results based on active mode
const currentResults = computed(() => {
  if (activeMode.value === 'semantic') {
    return ragResults.value
  } else if (activeMode.value === 'name') {
    return linkFilesResults.value as (SearchResult | LinkFileResult)[]
  }
  return []
})

// Computed property for loading state
const isLoading = ref(false)
const isSearchMode = computed(() => activeMode.value === 'semantic' || activeMode.value === 'name')

// Image error handler (simple function for Vue template)
function handleImageError(event: Event) {
  const target = event.target as HTMLImageElement
  target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgdmlld0JveD0iMCAwIDIwMCAyMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMDAiIGZpbGw9IiNGNUY1RjUiLz48cGF0aCBkPSJNMTAwIDcwQzc3LjkuMSAxMDAgOTIuMjcgMTAwIDExMEMxMDAgMTMyLjczIDkyLjI3IDE2MCA3MCAxNjBDMTkuNzMgMTYwIDAgMTAwIDAgMTAwQzAgMTMyLjczIDI2LjczIDE2MCA2MCAxNjBDMTkyLjI3IDE2MCAyMDAgMTAwIDIwMCAxMDBDMjAwIDcwIDE3Mi43IDcwIDEwMCA3MFoiIGZpbGw9IiNFOEU4RSIvPjxwYXRoIGQ9Ik02MCA4MEw4MCAxMDVMNTAgMTM1SDcwTDEwMCAxMDVMMTIwIDEzNUgxNTBMMTMwIDkwTDEwMCA2MEw3MCA5MEg2MFoiIGZpbGw9IiNDOEM4QyIvPjwvc3ZnPg=='
}

definePageMeta({
  layout: 'default',
})

useHead({
  title: 'Browse Files - Art Management',
})
</script>

<template>
  <div class="p-6 max-w-[1440px] mx-auto">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Browse Files</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Find your files using semantic or name-based search</p>
    </div>

    <!-- Mode Switcher -->
    <div class="mb-6">
      <div class="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800">
        <button
          v-for="mode in modes"
          :key="mode.value"
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors',
            activeMode === mode.value
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          ]"
          @click="switchMode(mode.value as BrowseMode)"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- Semantic Search & Name Search Content -->
    <div v-if="isSearchMode" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <!-- Search Input Area -->
      <div class="mb-6 flex gap-2">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            v-model="searchQuery"
            :placeholder="activeMode === 'semantic' ? 'Search with natural language... (e.g., green landscape painting for living room)' : 'Search by filename or display name...'"
            class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @keyup.enter="handleSearchSubmit"
          />
        </div>
        <button
          @click="handleSearchSubmit"
          :disabled="isLoading || !searchQuery.trim()"
          class="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
          <Search v-else class="w-4 h-4" />
          {{ isLoading ? 'Searching...' : 'Search' }}
        </button>
        <button
          v-if="currentResults.length > 0 || searchError"
          @click="clearSearch"
          class="px-4 py-2.5 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          Clear
        </button>
      </div>

      <!-- Search Info -->
      <div v-if="ragQueryTimeMs > 0 && activeMode === 'semantic'" class="mb-4 text-sm text-gray-500 dark:text-gray-400">
        Found {{ currentResults.length }} results in {{ ragQueryTimeMs }}ms
      </div>

      <!-- Error Message -->
      <div
        v-if="searchError"
        class="mb-4 p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3"
      >
        <AlertCircle class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div>
          <p class="text-red-800 dark:text-red-200 font-medium">{{ searchError }}</p>
          <p v-if="searchError.includes('RAG service')" class="text-red-600 dark:text-red-400 text-sm mt-1">
            Make sure the RAG service is running on port 8079
          </p>
        </div>
      </div>

      <!-- Results Grid -->
      <div v-if="currentResults.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div
          v-for="(result, index) in currentResults"
          :key="index"
          class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-zoom-in"
          @click="openPreview(getFileId(result), getFilename(result))"
        >
          <!-- Image -->
          <div class="aspect-square bg-gray-100 dark:bg-gray-900 relative overflow-hidden">
            <img
              :src="getPreviewUrl(getFileId(result), 540)"
              :alt="getFilename(result)"
              class="w-full h-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
              @error="handleImageError"
            />
            <!-- Similarity Badge (only for semantic search) -->
            <div
              v-if="hasSimilarity(result)"
              class="absolute top-2 right-2 px-2 py-1 bg-black/70 text-white text-xs rounded-full"
            >
              {{ formatSimilarity(result.similarity) }}
            </div>
          </div>
          <!-- File Info -->
          <div class="p-2">
            <p
              class="text-sm text-gray-900 dark:text-gray-100 truncate"
              :title="getFilename(result)"
            >
              {{ getFilename(result) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div
        v-if="isLoading"
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4"
      >
        <div
          v-for="i in 6"
          :key="i"
          class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse"
        >
          <div class="aspect-square bg-gray-200 dark:bg-gray-700" />
          <div class="p-2">
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-if="!isLoading && searchQuery && !searchError && currentResults.length === 0"
        class="text-center py-12"
      >
        <FileImage class="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p class="text-gray-500 dark:text-gray-400 text-lg">No results found</p>
        <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Try a different search term</p>
      </div>
    </div>

    <!-- Browse All Tab Content -->
    <div v-else-if="activeMode === 'browse_all'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div class="text-center py-12">
        <FileImage class="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p class="text-gray-500 dark:text-gray-400 text-lg">Browse all files</p>
        <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Use Semantic Search or Name Search tabs to find files</p>
      </div>
    </div>

    <!-- By Shop Tab Content -->
    <div v-else-if="activeMode === 'by_shop'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div class="text-center py-12">
        <FileImage class="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p class="text-gray-500 dark:text-gray-400 text-lg">Files by Shop</p>
        <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Coming soon</p>
      </div>
    </div>

    <!-- By Account Tab Content -->
    <div v-else-if="activeMode === 'by_acc'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div class="text-center py-12">
        <FileImage class="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p class="text-gray-500 dark:text-gray-400 text-lg">Files by Account</p>
        <p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Coming soon</p>
      </div>
    </div>

    <!-- Image Preview Modal -->
    <ImagePreviewModal :state="previewState" :close="close" :navigate="navigate" />
  </div>
</template>
