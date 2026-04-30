<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Image as ImageIcon, Loader2, X, Upload, ChevronRight, Eye } from 'lucide-vue-next'
import { useLinkFiles } from '~/composables/useLinkFiles'
import { useImagePreview } from '~/composables/useImagePreview'
import ImagePreviewModal from '~/components/ImagePreviewModal.vue'
import type { LinkFileResult } from '~/types/linkFiles'

// Reference to file input element
const fileInput = ref<HTMLInputElement | null>(null)

const {
  searchMode,
  searchQuery,
  searchResults,
  showLinkMenu,
  selectedFile,
  selectedShopId,
  selectedAccountId,
  shops,
  accounts,
  uploadedImage,
  selectedHashMethod,
  exceedsLimit,
  searchLoading,
  uploadLoading,
  uploadError,
  searchError,
  searchByFilename,
  reverseSearch,
  linkFileToShopAccount,
  openLinkMenu,
  closeLinkMenu,
  onShopChange,
  onAccountChange,
  handleImageUpload,
  handleDrop,
  handleDragOver,
  switchMode,
  clearResults,
} = useLinkFiles()

// Image preview
const { open, close, navigate, state: previewState } = useImagePreview()

// Get enlarged preview URL (1080px)
function getEnlargedPreviewUrl(fileId: number): string {
  return `/api/files/preview-proxy/${fileId}?x=1080&y=1080`
}

// Open image preview modal
function openPreview(fileId: number, filename: string) {
  open({ fileId, filename, previewUrl: getEnlargedPreviewUrl(fileId) })
}

// Local state for link form
const linkSuccess = ref(false)
const linkError = ref<string | null>(null)

// Handle link submission
async function handleLinkSubmit() {
  if (!selectedFile.value || !selectedShopId.value || !selectedAccountId.value) return

  linkSuccess.value = false
  linkError.value = null

  try {
    await linkFileToShopAccount(selectedFile.value.fileId, selectedShopId.value, selectedAccountId.value)
    linkSuccess.value = true
    setTimeout(() => {
      closeLinkMenu()
      linkSuccess.value = false
    }, 1500)
  } catch (e: any) {
    linkError.value = e.statusMessage || 'Failed to link file. Please try again.'
  }
}

// Handle search input submit
function handleSearchSubmit() {
  if (searchMode.value === 'filename') {
    searchByFilename(searchQuery.value)
  }
}

// Handle image file input change
function handleFileInputChange(event: Event) {
  handleImageUpload(event)
}

// Get thumbnail URL for a file
function getPreviewUrl(file: LinkFileResult, size: number = 540): string {
  // If previewUrl already contains the proxy path, use it directly
  if (file.previewUrl) {
    if (file.previewUrl.includes('preview-proxy')) {
      // Ensure correct size parameters
      const url = new URL(file.previewUrl, window.location.origin)
      url.searchParams.set('x', String(size))
      url.searchParams.set('y', String(size))
      return url.toString()
    }
    return `/api/files/preview-proxy/${file.fileId}?x=${size}&y=${size}`
  }
  return `/api/files/preview-proxy/${file.fileId}?x=${size}&y=${size}`
}

// Get uploaded image preview URL (client-side)
const uploadedImagePreview = computed(() => {
  if (uploadedImage.value) {
    return URL.createObjectURL(uploadedImage.value)
  }
  return null
})

// Format distance for display
function formatDistance(distance: number | undefined): string {
  if (distance === undefined) return 'N/A'
  return distance.toFixed(2)
}
</script>

<template>
  <div class="p-6 max-w-[1440px] mx-auto">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Link Files</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Search for files and link them to your shops</p>
    </div>

    <!-- Mode Switcher -->
    <div class="mb-6">
      <div class="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800">
        <button
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors',
            searchMode === 'filename'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          ]"
          @click="switchMode('filename')"
        >
          Search by Name
        </button>
        <button
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors',
            searchMode === 'reverse'
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          ]"
          @click="switchMode('reverse')"
        >
          Reverse Search
        </button>
      </div>
    </div>

    <!-- Mode 1: Search by Name -->
    <div v-if="searchMode === 'filename'">
      <!-- Search Input -->
      <div class="mb-6">
        <div class="flex gap-2 max-w-xl">
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by filename or display name..."
              class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @keyup.enter="handleSearchSubmit"
            />
          </div>
          <button
            @click="handleSearchSubmit"
            :disabled="searchLoading || !searchQuery.trim()"
            class="px-6 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Loader2 v-if="searchLoading" class="w-5 h-5 animate-spin" />
            <span v-else>Search</span>
          </button>
        </div>
      </div>

      <!-- Search Error -->
      <div v-if="searchError" class="mb-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <p class="text-red-600 dark:text-red-400">{{ searchError }}</p>
      </div>

      <!-- Results Grid -->
      <div v-if="searchResults.length > 0" class="mt-6">
        <!-- Warning for insufficient search -->
        <div v-if="exceedsLimit" class="mb-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800">
          <p class="text-yellow-700 dark:text-yellow-400 text-sm">
            More than 10 results found. Your search term wasn't specific enough. Try refining your search query for better results.
          </p>
        </div>

        <!-- File Grid -->
        <div class="file-grid">
          <div
            v-for="file in searchResults"
            :key="file.fileId"
            class="file-grid-item group rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
            @click="openLinkMenu(file)"
          >
            <div class="aspect-square bg-gray-100 dark:bg-gray-800 relative">
              <img
                :src="getPreviewUrl(file, 540)"
                :alt="file.displayName || file.filename"
                class="w-full h-full object-cover"
                @error="(e) => { const target = e.target as HTMLImageElement; target.src = '' }"
              />
              <!-- Preview button (top-right corner) -->
              <button
                @click.stop="openPreview(file.fileId, file.filename)"
                class="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
                title="Preview image"
              >
                <Eye class="w-4 h-4 text-white" />
              </button>
              <!-- Link button (center, on group hover) -->
              <div class="absolute inset-0 pointer-events-none bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                <ChevronRight class="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <div class="p-3 bg-white dark:bg-gray-800">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate" :title="file.filename">
                {{ file.filename }}
              </p>
              <p v-if="file.displayName" class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                {{ file.displayName }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="searchLoading" class="flex items-center justify-center py-12">
        <Loader2 class="w-8 h-8 animate-spin text-gray-400" />
      </div>

      <!-- Empty State -->
      <div v-if="!searchResults.length && !searchLoading && !searchError" class="text-center py-12">
        <ImageIcon class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
        <p class="text-gray-500 dark:text-gray-400">Enter a search term to find files</p>
      </div>
    </div>

    <!-- Mode 2: Reverse Search -->
    <div v-if="searchMode === 'reverse'">
      <!-- Upload Area (shown when no image uploaded) -->
      <div v-if="!uploadedImage && !uploadLoading" class="mb-6">
        <div
          class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-12 text-center cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
          @drop="handleDrop"
          @dragover="handleDragOver"
          @click="fileInput?.click()"
        >
          <Upload class="w-12 h-12 text-gray-400 mx-auto mb-3" />
          <p class="text-gray-600 dark:text-gray-400 mb-2">Drag and drop an image here, or click to select</p>
          <p class="text-sm text-gray-400 dark:text-gray-500">Supports JPG, PNG, WEBP</p>
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="handleFileInputChange"
          />
        </div>
      </div>

      <!-- Hash Method Selector -->
      <div v-if="uploadedImage" class="mb-6">
        <div class="flex items-center gap-3">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Hash Method:</span>
          <select
            v-model="selectedHashMethod"
            class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          >
            <option value="whash">Wavelet Hash (whash)</option>
            <option value="ahash">Average Hash (ahash)</option>
            <option value="phash">Perceptual Hash (phash)</option>
            <option value="average">Average (all methods)</option>
          </select>
          <button
            @click="uploadedImage && reverseSearch(uploadedImage)"
            :disabled="uploadLoading"
            class="ml-auto px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Loader2 v-if="uploadLoading" class="w-5 h-5 animate-spin" />
            <span v-else>Search</span>
          </button>
          <button
            v-if="!uploadLoading"
            @click="clearResults"
            class="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      <!-- Upload/Search Error -->
      <div v-if="uploadError || searchError" class="mb-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
        <p class="text-red-600 dark:text-red-400">{{ uploadError || searchError }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="uploadLoading" class="flex items-center justify-center py-12">
        <Loader2 class="w-8 h-8 animate-spin text-gray-400 mr-3" />
        <p class="text-gray-600 dark:text-gray-400">Calculating hashes and searching...</p>
      </div>

      <!-- Results -->
      <div v-if="searchResults.length > 0 && !uploadLoading" class="reverse-search-results">
        <!-- Top Row: Uploaded Image + Best Match -->
        <div class="top-row">
          <!-- Uploaded Image -->
          <div class="top-row-item">
            <div class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-gray-100 dark:bg-gray-800">
              <div class="aspect-square">
                <img
                  v-if="uploadedImagePreview"
                  :src="uploadedImagePreview"
                  alt="Uploaded image"
                  class="w-full h-full object-contain"
                />
              </div>
              <div class="p-3 bg-white dark:bg-gray-800">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {{ uploadedImage?.name || 'Uploaded Image' }}
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Your image</p>
              </div>
            </div>
          </div>

          <!-- Best Match -->
          <div class="top-row-item">
            <div
              v-if="searchResults[0]"
              class="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors bg-gray-100 dark:bg-gray-800"
            >
              <div class="aspect-square relative">
                <img
                  :src="getPreviewUrl(searchResults[0], 540)"
                  :alt="searchResults[0].displayName || searchResults[0].filename"
                  class="w-full h-full object-cover"
                  @error="(e) => { const target = e.target as HTMLImageElement; target.src = '' }"
                />
                <!-- Preview button (top-right corner) -->
                <button
                  @click.stop="openPreview(searchResults[0].fileId, searchResults[0].filename)"
                  class="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
                  title="Preview image"
                >
                  <Eye class="w-4 h-4 text-white" />
                </button>
              </div>
              <div class="p-3 bg-white dark:bg-gray-800">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {{ searchResults[0].filename }}
                </p>
                <p v-if="searchResults[0].displayName" class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                  {{ searchResults[0].displayName }}
                </p>
                <p class="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  Distance: {{ formatDistance(searchResults[0].combinedDistance) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- 3x3 Grid of Other Matches -->
        <div class="bottom-grid">
          <div
            v-for="file in searchResults.slice(1, 10)"
            :key="file.fileId"
            class="bottom-grid-item rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
            @click="openLinkMenu(file)"
          >
            <div class="aspect-square bg-gray-100 dark:bg-gray-800 relative">
              <img
                :src="getPreviewUrl(file, 180)"
                :alt="file.displayName || file.filename"
                class="w-full h-full object-cover"
                @error="(e) => { const target = e.target as HTMLImageElement; target.src = '' }"
              />
              <!-- Preview button (top-right corner) -->
              <button
                @click.stop="openPreview(file.fileId, file.filename)"
                class="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full hover:bg-black/70 transition-colors"
                title="Preview image"
              >
                <Eye class="w-4 h-4 text-white" />
              </button>
            </div>
            <div class="p-2 bg-white dark:bg-gray-800">
              <p class="text-xs font-medium text-gray-900 dark:text-gray-100 truncate" :title="file.filename">
                {{ file.filename }}
              </p>
              <p class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
                dist: {{ formatDistance(file.combinedDistance) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Link Option Menu -->
    <Teleport to="body">
      <Transition name="menu">
        <div v-if="showLinkMenu" class="fixed inset-0 z-50 flex justify-end" @click.self="closeLinkMenu">
          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/30" @click="closeLinkMenu"></div>
          
          <!-- Menu Panel -->
          <div class="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-xl border-l border-gray-200 dark:border-gray-700 flex flex-col">
            <!-- Header -->
            <div class="p-6 border-b border-gray-200 dark:border-gray-700">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Link File</h2>
                <button
                  @click="closeLinkMenu"
                  class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
                >
                  <X class="w-5 h-5" />
                </button>
              </div>
              
              <!-- Selected File Preview -->
              <div v-if="selectedFile" class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                <img
                  :src="getPreviewUrl(selectedFile, 64)"
                  :alt="selectedFile.filename"
                  class="w-16 h-16 rounded object-cover"
                  @error="(e) => { const target = e.target as HTMLImageElement; target.src = '' }"
                />
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ selectedFile.filename }}</p>
                  <p v-if="selectedFile.displayName" class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ selectedFile.displayName }}</p>
                </div>
              </div>
            </div>

            <!-- Form -->
            <div class="flex-1 p-6 overflow-y-auto">
              <!-- Link Success -->
              <div v-if="linkSuccess" class="p-4 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 mb-4">
                <p class="text-green-600 dark:text-green-400 text-sm">File linked successfully!</p>
              </div>

              <!-- Link Error -->
              <div v-if="linkError" class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 mb-4">
                <p class="text-red-600 dark:text-red-400 text-sm">{{ linkError }}</p>
              </div>

              <!-- Shop Selection -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Shop <span class="text-red-500">*</span>
                </label>
                <select
                  v-model="selectedShopId"
                  @change="onShopChange(selectedShopId!)"
                  class="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
                >
                  <option :value="null" disabled>Select a shop</option>
                  <option v-for="shop in shops" :key="shop.shop_id" :value="shop.shop_id">
                    {{ shop.shop_name }}
                  </option>
                </select>
              </div>

              <!-- Account Selection -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Account <span class="text-red-500">*</span>
                </label>
                <select
                  v-model="selectedAccountId"
                  @change="onAccountChange(selectedAccountId!)"
                  :disabled="!selectedShopId"
                  class="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <option :value="null" disabled>Select an account</option>
                  <option v-for="account in accounts" :key="account.account_id" :value="account.account_id">
                    {{ account.account_name }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Footer -->
            <div class="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
              <button
                @click="closeLinkMenu"
                class="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                @click="handleLinkSubmit"
                :disabled="!selectedShopId || !selectedAccountId"
                class="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Link File
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Image Preview Modal -->
    <ImagePreviewModal :state="previewState" :close="close" :navigate="navigate" />
  </div>
</template>

<style scoped>
/* Mode 1: Filename Search Grid */
.file-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  max-width: 1080px;
  margin: 0 auto;
}

.file-grid-item {
  max-width: 540px;
  margin: 0 auto;
  width: 100%;
}

/* Mode 2: Reverse Search Layout */
.reverse-search-results {
  max-width: 1080px;
  margin: 0 auto;
}

.top-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.top-row-item {
  max-width: 540px;
  margin: 0 auto;
  width: 100%;
}

.bottom-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.bottom-grid-item {
  max-width: 180px;
  margin: 0 auto;
  width: 100%;
}

/* Menu Transitions */
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.2s ease;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
}

.menu-enter-active .relative,
.menu-leave-active .relative {
  transition: transform 0.2s ease;
}

.menu-enter-from .relative,
.menu-leave-to .relative {
  transform: translateX(100%);
}
</style>
