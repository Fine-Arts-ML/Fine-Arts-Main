<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { Search, Image as ImageIcon, Loader2, ChevronRight, Trash2, X, CheckCircle2, Circle, Eye, EyeOff } from 'lucide-vue-next'
import { useLinkedFiles } from '~/composables/useLinkedFiles'
import { useImagePreview } from '~/composables/useImagePreview'
import ImagePreviewModal from '~/components/ImagePreviewModal.vue'
import type { Shop } from '~/types/shop'

// Fetch all shops for the initial list
const allShops = ref<Shop[]>([])
const shopsLoading = ref(false)

async function fetchShops() {
  shopsLoading.value = true
  try {
    allShops.value = await $fetch('/api/shops')
  } catch (e: any) {
    console.error('Failed to fetch shops:', e)
  } finally {
    shopsLoading.value = false
  }
}

// Linked Files composable
const {
  selectedShop: lfSelectedShop,
  selectedAccount: lfSelectedAccount,
  publishedFilter: lfPublishedFilter,
  searchQuery: lfSearchQuery,
  linkedFiles: lfLinkedFiles,
  shopAccounts: lfShopAccounts,
  loading: lfLoading,
  hasMore: lfHasMore,
  selectShop: lfSelectShop,
  selectAccount: lfSelectAccount,
  goBackToShopList: lfGoBackToShopList,
  goBackToShopView: lfGoBackToShopView,
  performSearch: lfPerformSearch,
  setPublishedFilter: lfSetPublishedFilter,
  togglePublished: lfTogglePublished,
  loadMore: lfLoadMore,
  unlinkFile: lfUnlinkFile,
  setupResizeObserver: lfSetupResizeObserver,
  visibleRows: lfVisibleRows,
} = useLinkedFiles()

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

// Confirmation sidebar state
const showUnlinkConfirm = ref(false)
const unlinkConfirmFile = ref<{
  fileId: number;
  filename: string;
  accountId?: number;
  accountNames?: string[];
  accountIds?: number[];
} | null>(null)
const selectedUnlinkAccountId = ref<number | undefined>(undefined)
const unlinking = ref(false)

function openUnlinkConfirm(file: {
  fileId: number | bigint;
  filename: string;
  accountId: number | bigint | null;
  accountNames?: string[];
  accountIds?: number[];
}) {
  const accountNames = file.accountNames || (file.accountId ? [`Account ${file.accountId}`] : [])
  const accountIds = file.accountIds || (file.accountId ? [Number(file.accountId)] : [])
  
  unlinkConfirmFile.value = {
    fileId: Number(file.fileId),
    filename: file.filename,
    accountId: file.accountId ? Number(file.accountId) : undefined,
    accountNames,
    accountIds,
  }
  
  // If multiple accounts, show account selection; otherwise pre-select the only account
  if (accountNames.length > 1) {
    selectedUnlinkAccountId.value = undefined // Let user choose
  } else if (accountIds.length > 0) {
    selectedUnlinkAccountId.value = accountIds[0]
  } else {
    selectedUnlinkAccountId.value = undefined
  }
  
  showUnlinkConfirm.value = true
}

async function confirmUnlink() {
  if (!unlinkConfirmFile.value) return
  
  // If multiple accounts and none selected, user needs to choose
  if (unlinkConfirmFile.value.accountNames && unlinkConfirmFile.value.accountNames.length > 1 && !selectedUnlinkAccountId.value) {
    return
  }
  
  unlinking.value = true
  try {
    await lfUnlinkFile(unlinkConfirmFile.value.fileId, selectedUnlinkAccountId.value)
    showUnlinkConfirm.value = false
    unlinkConfirmFile.value = null
    selectedUnlinkAccountId.value = undefined
  } catch (e: any) {
    console.error('[files.vue] Failed to unlink file:', e)
  } finally {
    unlinking.value = false
  }
}

function closeUnlinkConfirm() {
  showUnlinkConfirm.value = false
  unlinkConfirmFile.value = null
  selectedUnlinkAccountId.value = undefined
}

function onAccountSelect(accountId: number) {
  selectedUnlinkAccountId.value = accountId
}

// File list container ref for ResizeObserver
const fileListContainerRef = ref<HTMLElement | null>(null)
let lfObserverInitialized = false

// Setup ResizeObserver when component mounts
onMounted(async () => {
  await fetchShops()
  await nextTick()
  if (!lfObserverInitialized) {
    lfObserverInitialized = true
    lfSetupResizeObserver(fileListContainerRef.value)
  }
})

onUnmounted(() => {
  // Composable handles cleanup internally
})

// Handle file list scroll for lazy loading thumbnails
function onFileListScroll(event: Event) {
  const container = event.target as HTMLElement
  const images = container.querySelectorAll('img[data-lazy="true"]')
  images.forEach(img => {
    const rect = img.getBoundingClientRect()
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      const src = img.getAttribute('data-src')
      if (src && !img.src) {
        img.src = src
        img.removeAttribute('data-src')
        img.removeAttribute('data-lazy')
      }
    }
  })
}

// Get thumbnail URL
// Note: previewUrl is now transformed by the backend to include the full Nextcloud URL
// with actual dimensions, so we only need a fallback for missing previewUrl
function getThumbnailUrl(file: { fileId: number | bigint; previewUrl: string | null }) {
  if (file.previewUrl) {
    return file.previewUrl
  }
  // Fallback: no local thumbnail endpoint exists yet
  // Return empty to show placeholder icon
  return ''
}
</script>

<template>
  <div class="p-6">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Linked Files</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Browse and search files linked to your shops</p>
    </div>

    <!-- STATE: No Selection (Shop List View) -->
    <div v-if="!lfSelectedShop" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <div v-if="shopsLoading" class="p-12 text-center">
        <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">Loading shops...</p>
      </div>

      <div v-else-if="allShops.length === 0" class="p-12 text-center">
        <p class="text-gray-500 dark:text-gray-400">No shops found. Add a shop to get started.</p>
      </div>

      <div v-else class="divide-y divide-gray-200 dark:divide-gray-700">
        <button
          v-for="shop in allShops"
          :key="shop.shop_id"
          @click="lfSelectShop(shop)"
          class="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-left"
        >
          <span class="font-medium text-gray-900 dark:text-gray-100">{{ shop.shop_name }}</span>
          <span class="text-sm text-gray-500 dark:text-gray-400">
            {{ shop.account_count ?? 0 }} accounts · {{ shop.file_count ?? 0 }} files
          </span>
        </button>
      </div>
    </div>

    <!-- STATE: Shop Selected (Shop + Accounts + Files) -->
    <!-- STATE: Account Selected (Shop -> Account + Files) -->
    <div v-else class="space-y-4">
      <!-- Header with Shop/Account Navigation + Search -->
      <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <!-- Shop Name (and optional Account breadcrumb) -->
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <!-- Shop Name (clickable to go back to shop list) + Account Breadcrumb -->
          <div class="flex items-center gap-2 mb-3">
            <button
              @click="lfGoBackToShopList"
              class="text-lg font-bold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              {{ lfSelectedShop?.shop_name }}
            </button>

            <!-- Account Breadcrumb (shown when account is selected, clickable to go back to shop view) -->
            <template v-if="lfSelectedAccount">
              <ChevronRight class="w-4 h-4 text-gray-400" />
              <button
                @click="lfGoBackToShopView"
                class="text-lg font-bold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              >
                {{ lfSelectedAccount.accountName }}
              </button>
            </template>
          </div>

          <!-- Account List (shown when only shop is selected, not when account is drilled into) -->
          <div v-if="!lfSelectedAccount" class="divide-y divide-gray-200 dark:divide-gray-700">
            <button
              v-for="account in lfShopAccounts"
              :key="Number(account.accountId)"
              @click="lfSelectAccount(account)"
              class="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left rounded"
            >
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ account.accountName }}</span>
              <span class="text-sm text-gray-500 dark:text-gray-400">{{ Number(account.fileCount) }} files</span>
            </button>
          </div>
        </div>

        <!-- Search Input and Published Filter (between accounts and file list) -->
        <div class="p-4">
          <div class="flex items-center gap-3">
            <!-- Search Input -->
            <div class="flex-1 relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                v-model="lfSearchQuery"
                @input="lfPerformSearch(($event.target as HTMLInputElement).value)"
                type="text"
                placeholder="Search filenames or display names..."
                class="w-full pl-10 pr-10 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 rounded-md text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <button
                v-if="lfSearchQuery"
                @click="lfPerformSearch('')"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ×
              </button>
            </div>

            <!-- Published Filter -->
            <div class="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
              <button
                @click="lfSetPublishedFilter('all')"
                :class="[
                  'px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5',
                  lfPublishedFilter === 'all'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                ]"
              >
                <CheckCircle2 class="w-3.5 h-3.5" />
                All
              </button>
              <button
                @click="lfSetPublishedFilter('true')"
                :class="[
                  'px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5',
                  lfPublishedFilter === 'true'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                ]"
              >
                <CheckCircle2 class="w-3.5 h-3.5" />
                Published
              </button>
              <button
                @click="lfSetPublishedFilter('false')"
                :class="[
                  'px-3 py-1.5 rounded text-xs font-medium transition-colors flex items-center gap-1.5',
                  lfPublishedFilter === 'false'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
                ]"
              >
                <Circle class="w-3.5 h-3.5" />
                Unpublished
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- File List -->
      <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <!-- Loading State -->
        <div v-if="lfLoading && lfLinkedFiles.length === 0" class="p-12 text-center">
          <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
          <p class="text-gray-500 dark:text-gray-400 mt-2">Loading files...</p>
        </div>

        <!-- Empty State -->
        <div v-else-if="lfLinkedFiles.length === 0" class="p-12 text-center">
          <ImageIcon class="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600" />
          <p class="text-gray-500 dark:text-gray-400 mt-2">
            {{ lfSearchQuery ? 'No files match your search' : 'No files found for this selection' }}
          </p>
        </div>

        <!-- File List -->
        <div
          v-else
          ref="fileListContainerRef"
          @scroll="onFileListScroll"
          class="divide-y divide-gray-200 dark:divide-gray-700 max-h-[calc(100vh-400px)] overflow-y-auto"
          style="min-height: 200px;"
        >
          <div
            v-for="file in lfLinkedFiles"
            :key="Number(file.fileId)"
            :class="[
              'flex items-center gap-4 px-4 py-2 group',
              (file.accountNames && file.accountNames.length > 1)
                ? 'bg-red-50 dark:bg-red-950/20 hover:bg-red-100 dark:hover:bg-red-950/30 transition-colors'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors'
            ]"
          >
            <!-- Thumbnail (clickable for preview) -->
            <div
              class="flex-shrink-0 w-16 h-16 rounded overflow-hidden bg-gray-200 dark:bg-gray-700 flex items-center justify-center cursor-zoom-in"
              @click="openPreview(Number(file.fileId), file.filename)"
            >
              <img
                v-if="file.previewUrl"
                :src="file.previewUrl"
                :alt="file.filename"
                class="w-16 h-16 object-cover"
                @error="img => (img.target as HTMLImageElement).style.display = 'none'"
              />
              <ImageIcon v-else class="w-8 h-8 text-gray-400" />
            </div>

            <!-- File Info -->
            <div class="flex-1 min-w-0">
              <!-- Published Indicator and Account Names -->
              <div class="flex items-center gap-2 mb-1">
                <!-- Published Badge -->
                <button
                  @click="lfSetPublishedFilter(file.published ? 'false' : 'true')"
                  class="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium transition-colors"
                  :class="[
                    file.published
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
                  ]"
                  :title="file.published ? 'Click to filter unpublished' : 'Click to filter published'"
                >
                  <CheckCircle2 v-if="file.published" class="w-3.5 h-3.5" />
                  <Circle v-else class="w-3.5 h-3.5" />
                  {{ file.published ? 'Published' : 'Unpublished' }}
                </button>

                <!-- Toggle Published Button -->
                <button
                  @click="lfTogglePublished(file.fileId, !file.published)"
                  class="flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-colors"
                  :class="[
                    file.published
                      ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50'
                      : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 hover:bg-blue-200 dark:hover:bg-blue-900/50'
                  ]"
                  :title="file.published ? 'Click to unpublish' : 'Click to publish'"
                >
                  <ToggleIcon v-if="file.published" class="w-3.5 h-3.5" />
                  <ToggleIcon v-else class="w-3.5 h-3.5" />
                  {{ file.published ? 'Unpublish' : 'Publish' }}
                </button>

                <!-- Account Names (only shown in shop view, not account view) -->
                <div v-if="!lfSelectedAccount" class="text-xs text-gray-500 dark:text-gray-400">
                  <template v-if="file.accountNames && file.accountNames.length > 1">
                    <span v-for="(acct, idx) in file.accountNames" :key="idx">
                      <template v-if="idx > 0">, </template>
                      {{ acct }}
                    </span>
                  </template>
                  <template v-else>
                    {{ file.accountName }}
                  </template>
                </div>
              </div>

              <!-- Display Name or Filename -->
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="file.displayName" class="text-sm text-gray-900 dark:text-gray-100">
                  {{ file.displayName }}
                </span>
                <span v-else class="text-sm text-gray-900 dark:text-gray-100">
                  {{ file.filename }}
                </span>
              </div>

              <!-- Show filename below display name if present -->
              <div v-if="file.displayName" class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
                {{ file.filename }}
              </div>
            </div>

            <!-- Unlink Button (visible on hover) -->
            <button
              @click="openUnlinkConfirm(file)"
              class="flex-shrink-0 opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-all"
              title="Unlink file"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Load More Button -->
        <div v-if="lfHasMore && lfLinkedFiles.length > 0" class="p-4 border-t border-gray-200 dark:border-gray-700 text-center">
          <button
            @click="lfLoadMore"
            :disabled="lfLoading"
            class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 mx-auto"
          >
            <Loader2 v-if="lfLoading" class="w-4 h-4 animate-spin" />
            {{ lfLoading ? 'Loading...' : 'Load More' }}
          </button>
        </div>

        <!-- Results Count -->
        <div v-if="lfLinkedFiles.length > 0" class="px-4 py-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
          Showing {{ lfLinkedFiles.length }} files
          <template v-if="lfSelectedAccount"> for account {{ lfSelectedAccount.accountName }}</template>
          <template v-if="lfSearchQuery"> matching "{{ lfSearchQuery }}"</template>
          <template v-if="lfPublishedFilter !== 'all'"> · Filter: {{ lfPublishedFilter === 'true' ? 'Published only' : lfPublishedFilter === 'false' ? 'Unpublished only' : 'All' }}</template>
        </div>
      </div>
    </div>

    <!-- Confirmation Sidebar (right side) -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="translate-x-0"
      leave-to-class="translate-x-full"
    >
      <div v-if="showUnlinkConfirm" class="fixed right-0 top-0 h-full w-full max-w-sm bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 shadow-xl z-50">
        <!-- Sidebar Header -->
        <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Confirm Unlink</h3>
          <button
            @click="closeUnlinkConfirm"
            class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <!-- Sidebar Content -->
        <div class="p-6">
          <!-- File Preview -->
          <div class="flex items-center gap-4 mb-6 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div v-if="unlinkConfirmFile" class="flex-shrink-0 w-12 h-12 rounded overflow-hidden bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
              <img
                v-if="lfLinkedFiles.find(f => Number(f.fileId) === unlinkConfirmFile?.fileId)?.previewUrl"
                :src="lfLinkedFiles.find(f => Number(f.fileId) === unlinkConfirmFile?.fileId)?.previewUrl || ''"
                class="w-12 h-12 object-cover"
              />
              <ImageIcon v-else class="w-6 h-6 text-gray-400" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {{ unlinkConfirmFile?.filename }}
              </p>
              <p v-if="unlinkConfirmFile?.accountNames && unlinkConfirmFile.accountNames.length > 1" class="text-xs text-gray-500 dark:text-gray-400">
                Linked to {{ unlinkConfirmFile.accountNames.length }} accounts
              </p>
              <p v-else class="text-xs text-gray-500 dark:text-gray-400">
                Single account
              </p>
            </div>
          </div>

          <!-- Account Selection (when file is linked to multiple accounts) -->
          <div v-if="unlinkConfirmFile?.accountNames && unlinkConfirmFile.accountNames.length > 1" class="mb-6">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select account to unlink from:
            </label>
            <div class="space-y-2">
              <button
                v-for="(accountName, idx) in unlinkConfirmFile.accountNames"
                :key="accountName"
                @click="onAccountSelect(unlinkConfirmFile.accountIds?.[idx] || 0)"
                :class="[
                  'w-full text-left px-4 py-3 rounded-lg border transition-colors flex items-center justify-between',
                  selectedUnlinkAccountId === (unlinkConfirmFile.accountIds?.[idx] || 0)
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750'
                ]"
              >
                <span class="font-medium">{{ accountName }}</span>
                <span
                  :class="[
                    'w-4 h-4 rounded-full border flex items-center justify-center',
                    selectedUnlinkAccountId === (unlinkConfirmFile.accountIds?.[idx] || 0)
                      ? 'border-blue-500 bg-blue-500'
                      : 'border-gray-300 dark:border-gray-600'
                  ]"
                >
                  <span
                    v-if="selectedUnlinkAccountId === (unlinkConfirmFile.accountIds?.[idx] || 0)"
                    class="w-2 h-2 rounded-full bg-white"
                  />
                </span>
              </button>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
              Choose which account's link to this file should be removed. The file will remain linked to the other accounts.
            </p>
          </div>

          <!-- Confirmation Message -->
          <div class="mb-6">
            <p class="text-sm text-gray-700 dark:text-gray-300">
              Are you sure you want to unlink
              <span class="font-medium">{{ unlinkConfirmFile?.filename }}</span>
              from
              <span class="font-medium">{{ lfSelectedShop?.shop_name }}</span>
              <template v-if="unlinkConfirmFile?.accountNames && unlinkConfirmFile.accountNames.length > 1">
                <span> (Account: </span>
                <span class="font-medium">{{ selectedUnlinkAccountId ? (unlinkConfirmFile.accountNames[unlinkConfirmFile.accountIds?.indexOf(selectedUnlinkAccountId) || 0] || 'Unknown') : 'Select one' }}</span>
                <span>)</span>
              </template>
              <template v-else-if="unlinkConfirmFile?.accountId">
                <span> (Account: {{ unlinkConfirmFile.accountId }})</span>
              </template>
              ?
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
              This will remove the file from the
              <span class="font-mono">bre_file_junction</span>
              table.
            </p>
            <p v-if="!unlinkConfirmFile?.accountNames || unlinkConfirmFile.accountNames.length <= 1" class="text-xs text-amber-600 dark:text-amber-400 mt-2">
              ⚠ This will remove the file from this shop across ALL accounts.
            </p>
          </div>
        </div>

        <!-- Sidebar Footer -->
        <div class="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
          <div class="flex gap-3">
            <button
              @click="closeUnlinkConfirm"
              :disabled="unlinking"
              class="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              @click="confirmUnlink"
              :disabled="unlinking || (unlinkConfirmFile?.accountNames && unlinkConfirmFile.accountNames.length > 1 && !selectedUnlinkAccountId)"
              class="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Loader2 v-if="unlinking" class="w-4 h-4 animate-spin" />
              {{ unlinking ? 'Unlinking...' : 'Unlink' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Overlay -->
    <div
      v-if="showUnlinkConfirm"
      @click="closeUnlinkConfirm"
      class="fixed inset-0 bg-black/30 z-40"
    />

    <!-- Image Preview Modal -->
    <ImagePreviewModal :state="previewState" :close="close" :navigate="navigate" />
  </div>
</template>
