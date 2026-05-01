<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Image as ImageIcon, Loader2, X, Upload, ChevronRight, Eye, CheckCircle2, Circle, Maximize2 } from 'lucide-vue-next'
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
  published,
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

// Get selected shop name from shops array
const selectedShopName = computed(() => {
  if (!selectedShopId.value) return '[shop]'
  const shop = shops.value.find(s => s.shop_id === selectedShopId.value)
  return shop?.shop_name || '[shop]'
})

// Handle link submission
async function handleLinkSubmit() {
  if (!selectedFile.value || !selectedShopId.value || !selectedAccountId.value) return

  linkSuccess.value = false
  linkError.value = null

  try {
    await linkFileToShopAccount(selectedFile.value.fileId, selectedShopId.value, selectedAccountId.value, published.value)
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
    <div class="flex items-center gap-4 mb-6">
      <button
        :class="[
          'px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
          searchMode === 'filename'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
        ]"
        @click="switchMode('filename')"
      >
        <Search class="w-4 h-4" />
        Filename Search
      </button>
      <button
        :class="[
          'px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2',
          searchMode === 'reverse'
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
        ]"
        @click="switchMode('reverse')"
      >
        <Upload class="w-4 h-4" />
        Reverse Image Search
      </button>
    </div>

    <!-- Mode 1: Filename Search -->
    <div v-if="searchMode === 'filename'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <!-- Search Input -->
      <div class="flex gap-3 mb-6">
        <div class="flex-1 relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            v-model="searchQuery"
            @keyup.enter="handleSearchSubmit"
            type="text"
            placeholder="Search by filename or display name..."
            class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button
          @click="handleSearchSubmit"
          :disabled="searchLoading || !searchQuery.trim()"
          class="px-6 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <Loader2 v-if="searchLoading" class="w-4 h-4 animate-spin" />
          Search
        </button>
      </div>

      <!-- Search Error -->
      <div v-if="searchError" class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 mb-4">
        <p class="text-red-600 dark:text-red-400 text-sm">{{ searchError }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="searchLoading" class="p-12 text-center">
        <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">Searching...</p>
      </div>

      <!-- Results Grid -->
      <div v-else-if="searchResults.length > 0">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Found {{ searchResults.length }} results
            <span v-if="exceedsLimit" class="text-amber-600 dark:text-amber-400">(limited to 10)</span>
          </p>
          <button
            @click="clearResults"
            class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Clear
          </button>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div
            v-for="file in searchResults"
            :key="file.fileId"
            class="group relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors cursor-pointer"
            @click="openLinkMenu(file)"
          >
            <!-- Thumbnail -->
            <div class="aspect-square bg-gray-100 dark:bg-gray-800 relative">
              <img
                :src="getPreviewUrl(file, 540)"
                :alt="file.filename"
                class="w-full h-full object-cover"
                @error="e => { (e.target as HTMLImageElement).style.display = 'none' }"
              />
              <!-- Enlarge Icon (Top Right) -->
              <button
                class="absolute top-2 right-2 z-10 p-1.5 rounded-md bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                @click.stop.prevent="openPreview(file.fileId, file.filename)"
              >
                <Maximize2 class="w-3.5 h-3.5" />
              </button>
              <!-- Link Button Overlay -->
              <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center pointer-events-none">
                <button
                  class="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
                  @click.stop="openLinkMenu(file)"
                >
                  <ChevronRight class="w-4 h-4" />
                  Link
                </button>
              </div>
            </div>
            <!-- File Info -->
            <div class="p-3 bg-white dark:bg-gray-900">
              <p class="text-xs font-medium text-gray-900 dark:text-gray-100 truncate" :title="file.filename">
                {{ file.filename }}
              </p>
              <p v-if="file.displayName" class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                {{ file.displayName }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!searchLoading && searchQuery" class="p-12 text-center">
        <ImageIcon class="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">No files found matching "{{ searchQuery }}"</p>
      </div>
    </div>

    <!-- Mode 2: Reverse Image Search -->
    <div v-else class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <!-- Hash Method Selection -->
      <div class="flex items-center gap-4 mb-6">
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Hash Method:</label>
        <select
          v-model="selectedHashMethod"
          class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        >
          <option value="whash">Whitened Hash</option>
          <option value="ahash">Average Hash</option>
          <option value="phash">Phase Hash</option>
        </select>
      </div>

      <!-- Upload Area -->
      <div
        class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-12 text-center cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
        @click="fileInput?.click()"
        @dragover.prevent
        @drop="handleDrop"
      >
        <Upload class="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p class="text-gray-600 dark:text-gray-400 mb-2">
          Drag and drop an image here, or click to select
        </p>
        <p class="text-sm text-gray-500 dark:text-gray-500">
          Supports JPG, PNG, WEBP
        </p>
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="hidden"
          @change="handleFileInputChange"
        />
      </div>

      <!-- Uploaded Image Preview -->
      <div v-if="uploadedImagePreview" class="mt-6">
        <div class="flex items-center gap-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
          <img
            :src="uploadedImagePreview"
            :alt="uploadedImage?.name || 'Uploaded image'"
            class="w-20 h-20 rounded object-cover"
          />
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {{ uploadedImage?.name }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              {{ uploadedImage ? (uploadedImage.size / 1024 / 1024).toFixed(2) : '0' }} MB
            </p>
          </div>
          <button
            v-if="!uploadLoading"
            @click="uploadedImage = null"
            class="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            <X class="w-4 h-4 text-gray-500" />
          </button>
        </div>

        <!-- Upload Button -->
        <button
          v-if="!uploadLoading && !searchResults.length"
          @click="uploadedImage && reverseSearch(uploadedImage)"
          class="mt-4 w-full px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          <Eye class="w-4 h-4" />
          Search for Similar Images
        </button>
      </div>

      <!-- Upload Error -->
      <div v-if="uploadError" class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 mt-4">
        <p class="text-red-600 dark:text-red-400 text-sm">{{ uploadError }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="uploadLoading || searchLoading" class="p-12 text-center mt-4">
        <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">Processing image...</p>
      </div>

      <!-- Results Grid -->
      <div v-else-if="searchResults.length > 0" class="mt-6">
        <div class="flex items-center justify-between mb-4">
          <p class="text-sm text-gray-600 dark:text-gray-400">
            Found {{ searchResults.length }} similar images
            <span v-if="exceedsLimit" class="text-amber-600 dark:text-amber-400">(limited to 10)</span>
          </p>
          <button
            @click="clearResults"
            class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            Clear
          </button>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          <div
            v-for="file in searchResults"
            :key="file.fileId"
            class="group relative rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 hover:border-blue-500 dark:hover:border-blue-400 transition-colors cursor-pointer"
            @click="openLinkMenu(file)"
          >
            <!-- Thumbnail -->
            <div class="aspect-square bg-gray-100 dark:bg-gray-800 relative">
              <img
                :src="getPreviewUrl(file, 540)"
                :alt="file.filename"
                class="w-full h-full object-cover"
                @error="e => { (e.target as HTMLImageElement).style.display = 'none' }"
              />
              <!-- Link Button Overlay -->
              <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <button
                  class="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
                  @click.stop="openLinkMenu(file)"
                >
                  <ChevronRight class="w-4 h-4" />
                  Link
                </button>
              </div>
            </div>
            <!-- File Info -->
            <div class="p-3 bg-white dark:bg-gray-900">
              <p class="text-xs font-medium text-gray-900 dark:text-gray-100 truncate" :title="file.filename">
                {{ file.filename }}
              </p>
              <p v-if="file.displayName" class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                {{ file.displayName }}
              </p>
              <p v-if="file.combinedDistance !== undefined" class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
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

              <!-- Published Toggle -->
              <div class="mb-4">
                <label class="flex items-center gap-3 cursor-pointer group">
                  <div class="relative">
                    <input
                      v-model="published"
                      type="checkbox"
                      class="sr-only"
                    />
                    <div :class="[
                      'w-10 h-6 rounded-full transition-colors',
                      published ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
                    ]"></div>
                    <div :class="[
                      'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform shadow',
                      published ? 'translate-x-4' : 'translate-x-0'
                    ]"></div>
                  </div>
                  <div>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100">
                      Published in {{ selectedShopName }}?
                    </span>
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                      Make this file available for purchase
                    </p>
                  </div>
                </label>
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

@media (min-width: 768px) {
  .file-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .file-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

/* Menu transition */
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.menu-enter-to,
.menu-leave-from {
  opacity: 1;
  transform: translateX(0);
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.dark ::-webkit-scrollbar-thumb {
  background: #4b5563;
}
</style>
