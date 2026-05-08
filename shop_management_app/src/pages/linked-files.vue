<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import {
  useLinkedFiles,
} from '~/composables/useLinkedFiles'
import type { LinkedFileResult } from '~/types/linkedFile'
import type { Shop } from '~/types/shop'
import {
  Search,
  Loader2,
  X,
  Image as ImageIcon,
  Trash2,
  Eye,
  EyeOff,
  ChevronRight,
  ChevronLeft,
  Filter,
  Edit3,
  Plus,
} from 'lucide-vue-next'

// Use the linked files composable
const {
  selectedShop,
  selectedAccount,
  publishedFilter,
  searchQuery,
  linkedFiles,
  shopAccounts,
  loading,
  searchLoading,
  hasMore,
  visibleRows,
  selectShop,
  selectAccount,
  goBackToShopList,
  goBackToShopView,
  performSearch,
  setPublishedFilter,
  togglePublished,
  updateDisplayNames,
  loadMore,
  unlinkFile,
  setupResizeObserver,
} = useLinkedFiles()

// Edit display name modal state
const showEditDisplayNameModal = ref(false)
const editingFileId = ref<number | null>(null)
const editingDisplayNames = ref<string[]>([])
const newDisplayNameInput = ref('')

// Shops state
const shops = ref<Shop[]>([])
const shopsLoading = ref(false)

// Fetch shops
async function fetchShops() {
  shopsLoading.value = true
  try {
    shops.value = await $fetch('/api/shops') as Shop[]
  } catch (e: any) {
    console.error('Failed to fetch shops:', e)
  } finally {
    shopsLoading.value = false
  }
}

// Preview URL helper
function getPreviewUrl(file: LinkedFileResult, size: number = 540): string {
  const fileId = Number(file.fileId)
  return `/api/files/preview-proxy/${fileId}?size=${size}`
}

// Published toggle helper
async function handlePublishedToggle(file: LinkedFileResult, newPublished: boolean) {
  const success = await togglePublished(Number(file.fileId), newPublished)
  if (!success) {
    alert('Failed to update published status')
  }
}

// Unlink helper
async function handleUnlink(file: LinkedFileResult, accountId?: number) {
  if (!confirm('Are you sure you want to unlink this file?')) return
  const success = await unlinkFile(Number(file.fileId), accountId ? Number(accountId) : undefined)
  if (!success) {
    alert('Failed to unlink file')
  }
}

// Viewport resize handling
let contentElement: HTMLElement | null = null

function handleResize(element: HTMLElement) {
  setupResizeObserver(element)
}

// Edit display name helpers
function openEditDisplayNameModal(file: LinkedFileResult) {
  editingFileId.value = file.fileId
  editingDisplayNames.value = [...(file.allDisplayNames ?? [])]
  newDisplayNameInput.value = ''
  showEditDisplayNameModal.value = true
}

function closeEditDisplayNameModal() {
  showEditDisplayNameModal.value = false
  editingFileId.value = null
  editingDisplayNames.value = []
  newDisplayNameInput.value = ''
}

function addDisplayName() {
  const name = newDisplayNameInput.value.trim()
  if (name && !editingDisplayNames.value.includes(name)) {
    editingDisplayNames.value.push(name)
    newDisplayNameInput.value = ''
  }
}

function removeDisplayName(index: number) {
  editingDisplayNames.value.splice(index, 1)
}

function handleDisplayNameKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addDisplayName()
  }
  if (event.key === 'Backspace' && newDisplayNameInput.value === '' && editingDisplayNames.value.length > 0) {
    editingDisplayNames.value.pop()
  }
}

async function saveDisplayNames() {
  if (editingFileId.value === null) return
  const success = await updateDisplayNames(editingFileId.value, editingDisplayNames.value)
  if (!success) {
    alert('Failed to update display names')
  }
  closeEditDisplayNameModal()
}

onMounted(() => {
  fetchShops()
})

onUnmounted(() => {
  // Composable handles cleanup
})
</script>

<template>
  <div class="p-6 max-w-[1440px] mx-auto">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Linked Files</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">View and manage files linked to your shops</p>
    </div>

    <!-- Breadcrumb Navigation -->
    <div v-if="!selectedShop" class="mb-6">
      <p class="text-sm text-gray-500 dark:text-gray-400">Select a shop to view its linked files</p>
    </div>
    <div v-else class="mb-4 flex items-center gap-2 text-sm">
      <button
        @click="goBackToShopList"
        class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 flex items-center gap-1"
      >
        <ChevronLeft class="w-4 h-4" />
        All Shops
      </button>
      <span class="text-gray-400">/</span>
      <span class="font-medium text-gray-900 dark:text-gray-100">
        {{ selectedShop?.shop_name || 'Shop' }}
      </span>
      <button
        v-if="selectedAccount"
        @click="goBackToShopView"
        class="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 flex items-center gap-1 ml-2"
      >
        <ChevronLeft class="w-4 h-4" />
        {{ selectedAccount.accountName }}
      </button>
    </div>

    <!-- Step 1: Shop Selection -->
    <div v-if="!selectedShop" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <div class="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Select a Shop</h2>
      </div>
      <div class="p-4">
        <div v-if="shopsLoading" class="p-12 text-center">
          <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
          <p class="text-gray-500 dark:text-gray-400 mt-2">Loading shops...</p>
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Shop Name</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="shop in shops"
                :key="shop.shop_id"
                class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                @click="selectShop(shop)"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-gray-900 dark:text-gray-100">{{ shop.shop_name }}</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Step 2: Account Selection (if shop has multiple accounts) -->
    <div v-else-if="!selectedAccount && shopAccounts.length > 1" class="mb-6">
      <div class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 class="font-semibold text-gray-900 dark:text-gray-100">
            Select Account for {{ selectedShop?.shop_name }}
          </h2>
          <button
            @click="selectShop(selectedShop!)"
            class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            View All Accounts
          </button>
        </div>
        <div class="p-4 overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Account Name</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Published</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Unpublished</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
              <tr
                v-for="account in shopAccounts"
                :key="Number(account.accountId)"
                class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer"
                @click="selectAccount(account)"
              >
                <td class="px-4 py-3">
                  <p class="font-medium text-gray-900 dark:text-gray-100 text-sm">{{ account.accountName }}</p>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                    {{ Number(account.publishedCount) || 0 }}
                  </span>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400">
                    {{ Number(account.unpublishedCount) || 0 }}
                  </span>
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ Number(account.fileCount) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Step 3: Linked Files Table -->
    <div v-else class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <!-- Toolbar -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex flex-col sm:flex-row gap-3">
          <!-- Search -->
          <div class="flex-1 relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              v-model="searchQuery"
              @input="performSearch(searchQuery)"
              type="text"
              placeholder="Search by filename..."
              class="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>

          <!-- Published Filter -->
          <div class="flex items-center gap-2">
            <Filter class="w-4 h-4 text-gray-400" />
            <select
              v-model="publishedFilter"
              @change="setPublishedFilter(publishedFilter)"
              class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 text-sm"
            >
              <option value="all">All</option>
              <option value="true">Published</option>
              <option value="false">Unpublished</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Files Table -->
      <div ref="handleResize" class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Preview</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Filename</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Display Name</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Account(s)</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Published</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr
              v-for="file in linkedFiles"
              :key="file.fileId"
              class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
            >
              <!-- Preview -->
              <td class="px-4 py-3">
                <img
                  :src="getPreviewUrl(file, 64)"
                  :alt="file.filename"
                  class="w-12 h-12 rounded object-cover"
                  @error="e => { (e.target as HTMLImageElement).style.display = 'none' }"
                />
              </td>
              <!-- Filename -->
              <td class="px-4 py-3">
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate max-w-[200px]" :title="file.filename">
                  {{ file.filename }}
                </p>
              </td>
              <!-- Display Name -->
              <td class="px-4 py-3">
                <div v-if="file.allDisplayNames && file.allDisplayNames.length > 0" class="flex flex-wrap gap-1">
                  <span
                    v-for="(name, idx) in file.allDisplayNames"
                    :key="idx"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400"
                  >
                    {{ name }}
                  </span>
                </div>
                <p v-else class="text-sm text-gray-400 dark:text-gray-500">-</p>
              </td>
              <!-- Account(s) -->
              <td class="px-4 py-3">
                <div v-if="file.accountNames && file.accountNames.length > 0" class="flex flex-wrap gap-1">
                  <span
                    v-for="(name, idx) in file.accountNames.slice(0, 2)"
                    :key="idx"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
                  >
                    {{ name }}
                  </span>
                  <span
                    v-if="file.accountNames.length > 2"
                    class="text-xs text-gray-500 dark:text-gray-400"
                  >
                    +{{ file.accountNames.length - 2 }}
                  </span>
                </div>
                <p v-else class="text-sm text-gray-400 dark:text-gray-500">-</p>
              </td>
              <!-- Published -->
              <td class="px-4 py-3">
                <button
                  @click="handlePublishedToggle(file, !file.published)"
                  class="flex items-center gap-1.5 text-sm"
                >
                  <Eye v-if="file.published" class="w-4 h-4 text-green-600 dark:text-green-400" />
                  <EyeOff v-else class="w-4 h-4 text-gray-400" />
                  <span :class="file.published ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'">
                    {{ file.published ? 'Yes' : 'No' }}
                  </span>
                </button>
              </td>
              <!-- Actions -->
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="openEditDisplayNameModal(file)"
                    class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                    title="Edit Display Names"
                  >
                    <Edit3 class="w-3.5 h-3.5" />
                    Edit
                  </button>
                  <button
                    @click="handleUnlink(file, Number(file.accountId))"
                    class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                    Unlink
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Loading State -->
      <div v-if="loading && linkedFiles.length === 0" class="p-12 text-center">
        <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">Loading linked files...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="!loading && linkedFiles.length === 0" class="p-12 text-center">
        <ImageIcon class="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600" />
        <p class="text-gray-500 dark:text-gray-400 mt-2">No linked files found</p>
        <p class="text-sm text-gray-400 dark:text-gray-500 mt-1">
          {{ searchQuery ? 'Try a different search term' : 'Files linked to this shop will appear here' }}
        </p>
      </div>

      <!-- Load More -->
      <div v-if="hasMore && linkedFiles.length > 0" class="p-4 border-t border-gray-200 dark:border-gray-700 text-center">
        <button
          @click="loadMore"
          :disabled="loading"
          class="px-6 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 mx-auto"
        >
          <Loader2 v-if="loading" class="w-4 h-4 animate-spin" />
          {{ loading ? 'Loading...' : 'Load More' }}
        </button>
      </div>

      <!-- Results Count -->
      <div v-if="linkedFiles.length > 0" class="p-3 border-t border-gray-200 dark:border-gray-700 text-center">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Showing {{ linkedFiles.length }} linked files
        </p>
      </div>
    </div>

    <!-- Edit Display Name Modal -->
    <Teleport to="body">
      <Transition enter-active-class="transition duration-200 ease-out" enter-from-class="translate-y-2 opacity-0" enter-to-class="translate-y-0 opacity-100" leave-active-class="transition duration-150 ease-in" leave-from-class="translate-y-0 opacity-100" leave-to-class="translate-y-2 opacity-0">
        <div v-if="showEditDisplayNameModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
          <!-- Backdrop -->
          <div class="fixed inset-0 bg-black/50" @click="closeEditDisplayNameModal"></div>
          
          <!-- Modal -->
          <div class="relative bg-white dark:bg-gray-900 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 w-full max-w-md z-10">
            <!-- Modal Header -->
            <div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Edit Display Names</h3>
              <button
                @click="closeEditDisplayNameModal"
                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
            
            <!-- Modal Body -->
            <div class="p-4">
              <!-- Current Display Names -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Display Names
                </label>
                <div v-if="editingDisplayNames.length === 0" class="text-sm text-gray-400 dark:text-gray-500 py-2">
                  No display names assigned
                </div>
                <div v-else class="flex flex-wrap gap-2 mb-2">
                  <span
                    v-for="(name, index) in editingDisplayNames"
                    :key="index"
                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400"
                  >
                    {{ name }}
                    <button
                      @click="removeDisplayName(index)"
                      class="hover:text-blue-600 dark:hover:text-blue-300 transition-colors"
                    >
                      <X class="w-3 h-3" />
                    </button>
                  </span>
                </div>
              </div>
              
              <!-- Add New Display Name -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Add New Display Name
                </label>
                <div class="flex gap-2">
                  <input
                    v-model="newDisplayNameInput"
                    @keydown="handleDisplayNameKeydown"
                    type="text"
                    placeholder="Type and press Enter to add..."
                    class="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button
                    @click="addDisplayName"
                    class="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                  >
                    <Plus class="w-4 h-4" />
                  </button>
                </div>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
                  Press Enter or comma to add, Backspace to remove last
                </p>
              </div>
            </div>
            
            <!-- Modal Footer -->
            <div class="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
              <button
                @click="closeEditDisplayNameModal"
                class="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                @click="saveDisplayNames"
                class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
table {
  table-layout: auto;
}
</style>
