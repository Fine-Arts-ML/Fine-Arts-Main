<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch, type Ref, onActivated } from 'vue'
import { useRagSearch, type SearchResult } from '~/composables/useRagSearch'
import { useImagePreview } from '~/composables/useImagePreview'
import ImagePreviewModal from '~/components/ImagePreviewModal.vue'
import type { Shop } from '~/types/shop'
import type { Account } from '~/types/account'
import type { LinkFileResult } from '~/types/linkFiles'
import { Search, Image as ImageIcon, Loader2, X, Upload, ChevronRight, Eye, CheckCircle2, Circle, Maximize2, SortAsc, SortDesc, Trash2, AlertCircle } from 'lucide-vue-next'
import { $fetch as $fetchOriginal } from 'ofetch'

// ========== Types ==========
type SearchMode = 'semantic' | 'name' | 'browse_all' | 'reverse'
type SortOption = 'fileid' | 'name'
type SortOrder = 'asc' | 'desc'

// ========== Image Preview ==========
const { open: openPreview, close: closePreview, navigate: navigatePreview, state: previewState } = useImagePreview()

// ========== RAG Search ==========
// ========== RAG Search ==========
const ragSearchState = useRagSearch()
const { search: ragSearch, loadMore: loadMoreRagSearch, clearResults: clearRagResults } = ragSearchState
// Use computed() to maintain reactivity when accessing reactive state properties
const ragHasMore = computed(() => ragSearchState.hasMore)
const ragTotalMatching = computed(() => ragSearchState.totalMatching)
const ragMinSimilarity = computed(() => ragSearchState.minSimilarity)
const ragIsLoadingMore = computed(() => ragSearchState.isLoadingMore)
const ragResults = ref<SearchResult[]>([])
const ragQueryTimeMs = ref(0)
const ragSearchQuery = ref('')
const semanticSentinelRef = ref<HTMLElement | null>(null)
const semanticSearchContainerRef = ref<HTMLElement | null>(null)
let semanticSearchObserver: IntersectionObserver | null = null
const semanticInfiniteScrollActive = ref(false)

// ========== Link Files (name search + reverse search + linking) ==========
const searchMode = ref<SearchMode>('semantic')
const searchQuery = ref('')
const searchLoading = ref(false)
const uploadLoading = ref(false)
const uploadError = ref<string | null>(null)
const searchError = ref<string | null>(null)
const exceedsLimit = ref(false)

// Name search results
const nameSearchResults = ref<LinkFileResult[]>([])

// Reverse search results
const reverseSearchResults = ref<LinkFileResult[]>([])
const uploadedImage = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
function triggerFileInput() {
  fileInputRef.value?.click()
}
const selectedHashMethod = ref<'whash' | 'ahash' | 'phash'>('whash')
const uploadedImagePreview = computed(() => uploadedImage.value ? URL.createObjectURL(uploadedImage.value) : null)

// Linking state
const showLinkMenu = ref(false)
const selectedFile = ref<LinkFileResult | null>(null)
const selectedShopId = ref<number | null>(null)
const selectedAccountId = ref<number | null>(null)
const shops = ref<Shop[]>([])
const accounts = ref<Account[]>([])
const published = ref(false)
const linkSuccess = ref(false)
const linkError = ref<string | null>(null)

// Display names (tag-style input)
const displayNameInput = ref('')
const displayNames = ref<string[]>([])
const isAddingDisplayName = ref(false)

function addDisplayName() {
  const name = displayNameInput.value.trim()
  console.log('[files.vue] addDisplayName called, name:', name, 'current displayNames:', displayNames.value)
  if (name && !displayNames.value.includes(name)) {
    displayNames.value.push(name)
    displayNameInput.value = ''
    console.log('[files.vue] After push, displayNames:', displayNames.value)
  }
}

function removeDisplayName(index: number) {
  displayNames.value.splice(index, 1)
}

function handleDisplayNameKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    addDisplayName()
  }
  if (event.key === 'Backspace' && displayNameInput.value === '' && displayNames.value.length > 0) {
    displayNames.value.pop()
  }
}

// Browse All state
const browseOffset = ref(0)
const browseLoading = ref(false)
const browseHasMore = ref(true)
const allLoadedFiles = ref<Array<{ fileId: number; filename: string; previewUrl?: string }>>([])
const displayedFiles = ref<Array<{ fileId: number; filename: string; previewUrl?: string }>>([])
const BROWSE_LIMIT = 48
const sortBy = ref<SortOption>('fileid')
const sortOrder = ref<SortOrder>('asc')
const isSortDropdownOpen = ref(false)
const filterQuery = ref('')
const showBackToTop = ref(false)
const showSemanticBackToTop = ref(false)
const browseContainerRef = ref<HTMLElement | null>(null)
const sentinelRef = ref<HTMLElement | null>(null)

// Shops loading
const shopsLoading = ref(false)

// ========== Computed ==========
const isSearchMode = computed(() => ['semantic', 'name'].includes(searchMode.value))
const isBrowseAllMode = computed(() => searchMode.value === 'browse_all')
const isReverseMode = computed(() => searchMode.value === 'reverse')

const currentResults = computed(() => {
  if (searchMode.value === 'semantic') return ragResults.value as any[]
  if (searchMode.value === 'name') return nameSearchResults.value as any[]
  return []
})

const filteredFiles = computed(() => {
  const q = filterQuery.value.trim().toLowerCase()
  if (!q) return displayedFiles.value
  return displayedFiles.value.filter(f => f.filename.toLowerCase().includes(q))
})

const filterCount = computed(() => filterQuery.value.trim() ? filteredFiles.value.length : 0)

const sortLabel = computed(() => {
  const field = sortBy.value === 'fileid' ? 'File ID' : 'Name'
  const order = sortOrder.value === 'asc' ? 'Ascending' : 'Descending'
  return `${field} (${order})`
})

const selectedShopName = computed(() => {
  if (!selectedShopId.value) return '[shop]'
  const shop = shops.value.find(s => s.shop_id === selectedShopId.value)
  return shop?.shop_name || '[shop]'
})

// Best match for reverse search (lowest distance)
const bestReverseMatch = computed(() => {
  if (searchMode.value !== 'reverse' || reverseSearchResults.value.length === 0) return null
  return reverseSearchResults.value.reduce((best, current) => {
    const bestDist = best.combinedDistance ?? best.whashDistance ?? 999999
    const curDist = current.combinedDistance ?? current.whashDistance ?? 999999
    return curDist < bestDist ? current : best
  })
})

const otherReverseMatches = computed(() => {
  if (searchMode.value !== 'reverse' || !bestReverseMatch.value) return []
  const bestId = bestReverseMatch.value?.fileId ?? 0
  return reverseSearchResults.value.filter(f => f.fileId !== bestId).slice(0, 9)
})

const modes = [
  { value: 'semantic' as SearchMode, label: 'Semantic Search' },
  { value: 'name' as SearchMode, label: 'Name Search' },
  { value: 'browse_all' as SearchMode, label: 'Browse All' },
  { value: 'reverse' as SearchMode, label: 'Reverse Search' },
]

// ========== Helpers ==========
function getPreviewUrl(fileId: number, size: number = 540): string {
  return `/api/files/preview-proxy/${fileId}?x=${size}&y=${size}`
}

function getEnlargedPreviewUrl(fileId: number): string {
  return `/api/files/preview-proxy/${fileId}?x=1080&y=1080`
}

function openPreviewModal(fileId: number, filename: string) {
  openPreview({ fileId, filename, previewUrl: getEnlargedPreviewUrl(fileId) })
}

function getFilename(result: any): string { return result.filename }
function getFileId(result: any): number { return result.fileId || result.file_id }

function formatSimilarity(score: number): string { return (score * 100).toFixed(1) + '%' }
function formatDistance(distance: number | undefined): string {
  if (distance === undefined) return 'N/A'
  return distance.toFixed(2)
}

// ========== Shops & Accounts ==========
async function fetchShops() {
  shopsLoading.value = true
  try {
    shops.value = await $fetch('/api/shops')
  } catch (e: any) {
    console.error('Failed to fetch shops:', e)
  } finally {
    shopsLoading.value = false
  }
}

async function fetchAccounts(shopId: number) {
  try {
    accounts.value = await $fetch(`/api/shops/${shopId}/accounts`)
  } catch (e: any) {
    console.error('Failed to fetch accounts:', e)
  }
}

// ========== Linking ==========
function openLinkMenu(file: LinkFileResult) {
  selectedFile.value = file
  showLinkMenu.value = true
  selectedShopId.value = null
  selectedAccountId.value = null
  accounts.value = []
  linkSuccess.value = false
  linkError.value = null
  if (selectedShopId.value) fetchAccounts(selectedShopId.value)
}

function closeLinkMenu() {
  showLinkMenu.value = false
  selectedFile.value = null
  published.value = false
  displayNames.value = []
  displayNameInput.value = ''
  isAddingDisplayName.value = false
}

function onShopChange(shopId: number) {
  selectedShopId.value = shopId
  selectedAccountId.value = null
  fetchAccounts(shopId)
}

function onAccountChange(accountId: number) {
  selectedAccountId.value = accountId
}

async function handleLinkSubmit() {
  if (!selectedFile.value || !selectedShopId.value || !selectedAccountId.value) return
  linkSuccess.value = false
  linkError.value = null
  try {
    const fileId = getFileId(selectedFile.value)
    await $fetch('/api/files/link-to-shop-account', {
      method: 'POST',
      body: {
        fileId,
        shopId: selectedShopId.value,
        accountId: selectedAccountId.value,
        published: published.value,
        displayNames: displayNames.value,
      },
    })
    linkSuccess.value = true
    setTimeout(() => { closeLinkMenu(); linkSuccess.value = false }, 1500)
  } catch (e: any) {
    linkError.value = e.statusMessage || 'Failed to link file. Please try again.'
  }
}

// ========== Semantic Search ==========
const SEMANTIC_LIMIT = 24
const SEMANTIC_MIN_SIMILARITY = 0.25

async function performSemanticSearch() {
  const query = searchQuery.value.trim()
  if (!query) { searchError.value = 'Please enter a search query'; return }
  searchLoading.value = true
  searchError.value = null
  ragResults.value = []
  ragQueryTimeMs.value = 0
  ragSearchQuery.value = query
  try {
    const response = await ragSearch(query, { top_k: SEMANTIC_LIMIT, min_similarity: SEMANTIC_MIN_SIMILARITY })
    ragResults.value = response.results
    ragQueryTimeMs.value = response.query_time_ms
  } catch (err: any) {
    searchError.value = err.message || 'Search failed. Please try again.'
  } finally {
    searchLoading.value = false
  }
}

// Load more semantic search results (infinite scroll)
async function loadMoreSemanticResults() {
  if (!ragHasMore.value || ragIsLoadingMore.value) return
  try {
    const response = await loadMoreRagSearch({ top_k: SEMANTIC_LIMIT, min_similarity: SEMANTIC_MIN_SIMILARITY })
    // The composable already appends to state.results, but we need to sync with our local ref
    ragResults.value = [...ragResults.value, ...response.results]
  } catch (err: any) {
    console.error('Failed to load more semantic results:', err)
  }
}

// ========== Name Search ==========
async function performNameSearch() {
  const query = searchQuery.value.trim()
  if (!query) { searchError.value = 'Please enter a search query'; return }
  searchLoading.value = true
  searchError.value = null
  try {
    const params = new URLSearchParams({ query: query.trim(), limit: '10', previewSize: '540' })
    const results = await $fetch(`/api/files/search-by-name?${params}`)
    nameSearchResults.value = results
    exceedsLimit.value = results.length >= 10
  } catch (e: any) {
    searchError.value = e.statusMessage || 'Search failed. Please try again.'
    nameSearchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

// ========== Browse All ==========
async function fetchBrowseFiles(append = false) {
  console.log('[BROWSE-ALL-FILES] fetchBrowseFiles called: append=', append, 'browseLoading=', browseLoading.value, 'browseHasMore=', browseHasMore.value, 'offset=', browseOffset.value)
  if (browseLoading.value || !browseHasMore.value) {
    console.log('[BROWSE-ALL-FILES] fetchBrowseFiles SKIPPED: loading=', browseLoading.value, 'hasMore=', browseHasMore.value)
    return
  }
  console.log('[BROWSE-ALL-FILES] fetchBrowseFiles PROCEEDING: fetching batch')
  browseLoading.value = true
  try {
    const params = new URLSearchParams({
      limit: String(BROWSE_LIMIT), offset: String(browseOffset.value),
      sortBy: sortBy.value, sortOrder: sortOrder.value,
    })
    console.log('[BROWSE-ALL-FILES] Fetching URL:', `/api/files/browse-all?${params}`)
    const results = await $fetch<Array<{ fileId: number; filename: string; previewUrl?: string }>>(`/api/files/browse-all?${params}`)
    console.log('[BROWSE-ALL-FILES] fetchBrowseFiles RESPONSE: received', results.length, 'results, append=', append, 'allLoaded before=', allLoadedFiles.value.length)
    if (results.length < BROWSE_LIMIT) {
      console.log('[BROWSE-ALL-FILES] WARNING: Got', results.length, 'results (< limit', BROWSE_LIMIT, '), setting browseHasMore=false')
      browseHasMore.value = false
    }
    if (append) {
      allLoadedFiles.value = [...allLoadedFiles.value, ...results]
      displayedFiles.value = [...displayedFiles.value, ...results]
    } else {
      allLoadedFiles.value = results
      displayedFiles.value = results
    }
    browseOffset.value += results.length
    console.log('[BROWSE-ALL-FILES] fetchBrowseFiles COMPLETE: offset=', browseOffset.value, 'displayed=', displayedFiles.value.length, 'allLoaded=', allLoadedFiles.value.length, 'hasMore=', browseHasMore.value)
  } catch (err: any) {
    console.error('[BROWSE-ALL-FILES] Failed to fetch browse files:', err)
  } finally {
    browseLoading.value = false
  }
}

function resetBrowseAll() {
  console.log('[BROWSE-ALL-FILES] resetBrowseAll called')
  allLoadedFiles.value = []
  displayedFiles.value = []
  browseOffset.value = 0
  browseHasMore.value = true
  filterQuery.value = ''
  showBackToTop.value = false
  console.log('[BROWSE-ALL-FILES] resetBrowseAll calling fetchBrowseFiles')
  fetchBrowseFiles()
}

// Re-observe sentinel when files change (after fetch)
watch(displayedFiles, () => {
  if (isBrowseAllMode.value) {
    nextTick(() => setupIntersectionObserver())
  }
}, { deep: true })

function toggleSortOrder() { sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'; resetBrowseAll() }
function setSortBy(option: SortOption) { sortBy.value = option; resetBrowseAll() }
function toggleSortDropdown() { isSortDropdownOpen.value = !isSortDropdownOpen.value }
function closeSortDropdown() { isSortDropdownOpen.value = false }
function clearFilter() { filterQuery.value = '' }

// ========== Reverse Search ==========
async function performReverseSearch(imageFile: File) {
  uploadLoading.value = true
  uploadError.value = null
  searchLoading.value = true
  searchError.value = null
  uploadedImage.value = imageFile
  reverseSearchResults.value = []
  try {
    const formData = new FormData()
    formData.append('image', imageFile)
    formData.append('hashMethod', selectedHashMethod.value)
    const results = await $fetch('/api/files/reverse-search', { method: 'POST', body: formData })
    reverseSearchResults.value = results
    exceedsLimit.value = results.length >= 10
  } catch (e: any) {
    uploadError.value = e.statusMessage || 'Reverse search failed. Please try again.'
    searchError.value = uploadError.value
    reverseSearchResults.value = []
  } finally {
    uploadLoading.value = false
    searchLoading.value = false
  }
}

function handleImageUpload(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) performReverseSearch(file)
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  const file = event.dataTransfer?.files[0]
  if (file && file.type.startsWith('image/')) performReverseSearch(file)
}

// ========== Mode Switching ==========
function switchMode(mode: SearchMode) {
  searchMode.value = mode
  if (!['semantic', 'name'].includes(mode)) {
    ragResults.value = []
    nameSearchResults.value = []
    reverseSearchResults.value = []
  }
  if (mode !== 'browse_all') filterQuery.value = ''
  if (mode === 'browse_all' && allLoadedFiles.value.length === 0) resetBrowseAll()
}

function handleSearchSubmit() {
  if (searchMode.value === 'semantic') performSemanticSearch()
  else if (searchMode.value === 'name') performNameSearch()
}

function clearSearch() {
  searchQuery.value = ''
  ragSearchQuery.value = ''
  ragResults.value = []
  nameSearchResults.value = []
  reverseSearchResults.value = []
  ragQueryTimeMs.value = 0
  searchError.value = null
  clearRagResults()
  teardownSemanticSearchObserver()
}

// ========== Semantic Search Infinite Scroll ==========
function setupSemanticSearchObserver() {
  const sentinel = semanticSentinelRef.value
  if (!sentinel) return

  if (semanticSearchObserver) {
    semanticSearchObserver.disconnect()
  }

  // Use the scrollable container as root so the observer triggers when the sentinel
  // scrolls into view within the container (not just the viewport).
  const container = semanticSearchContainerRef.value
  if (!container) return

  semanticSearchObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting && ragHasMore.value && !ragIsLoadingMore.value && searchMode.value === 'semantic') {
        loadMoreSemanticResults()
      }
    })
  }, { root: container, threshold: 0.1 })

  semanticSearchObserver.observe(sentinel)
  semanticInfiniteScrollActive.value = true
}

function teardownSemanticSearchObserver() {
  if (semanticSearchObserver) {
    semanticSearchObserver.disconnect()
    semanticSearchObserver = null
  }
  semanticInfiniteScrollActive.value = false
}

// Watch for semantic search results to set up observer
watch(ragResults, () => {
  if (searchMode.value === 'semantic' && ragResults.value.length > 0 && ragHasMore.value) {
    nextTick(() => setupSemanticSearchObserver())
  }
}, { deep: true })

// Watch for mode changes to teardown semantic observer
watch(searchMode, (newMode) => {
  if (newMode !== 'semantic') {
    teardownSemanticSearchObserver()
  } else if (ragResults.value.length > 0 && ragHasMore.value) {
    nextTick(() => setupSemanticSearchObserver())
  }
})

// ========== Click-outside handler ==========
function handleDocumentClick(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (isSortDropdownOpen.value && !target.closest('[class*="relative"]')?.querySelector('button')?.contains(target)) {
    closeSortDropdown()
  }
}

// ========== Lifecycle ==========
let scrollCleanup: (() => void) | null = null
let intersectionObserver: IntersectionObserver | null = null

function handleScroll() {
  const container = browseContainerRef.value
  if (!container) return
  
  const scrollTop = container.scrollTop
  const scrollHeight = container.scrollHeight
  const clientHeight = container.clientHeight
  const scrollRemaining = scrollHeight - scrollTop - clientHeight
  
  showBackToTop.value = scrollTop > clientHeight
  
  // Infinite scroll: trigger when within 200px of the bottom
  if (scrollRemaining <= 200 && browseHasMore.value && !browseLoading.value) {
    console.log('[BROWSE-ALL-FILES] handleScroll: Near bottom (scrollRemaining=', scrollRemaining, '), triggering fetchBrowseFiles(true)')
    fetchBrowseFiles(true)
  }
}

// ========== Semantic Search Scroll Handler ==========
let semanticScrollCleanup: (() => void) | null = null

function handleSemanticScroll() {
  const container = semanticSearchContainerRef.value
  if (!container) return
  showSemanticBackToTop.value = container.scrollTop > container.clientHeight
}

function scrollToSemanticTop() {
  const container = semanticSearchContainerRef.value
  if (container) {
    container.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

function setupIntersectionObserver() {
  console.log('[BROWSE-ALL-FILES] setupIntersectionObserver called')
  const sentinel = sentinelRef.value
  console.log('[BROWSE-ALL-FILES] sentinelRef.value:', sentinel)
  if (!sentinel) {
    console.log('[BROWSE-ALL-FILES] ABORTING: sentinelRef.value is null')
    return
  }

  // Disconnect existing observer to avoid duplicates
  if (intersectionObserver) {
    console.log('[BROWSE-ALL-FILES] Disconnecting existing observer')
    intersectionObserver.disconnect()
  }

  const container = browseContainerRef.value
  console.log('[BROWSE-ALL-FILES] browseContainerRef.value:', container)
  console.log('[BROWSE-ALL-FILES] Sentinel element:', sentinel.outerHTML?.substring(0, 100) || sentinel)
  
  // Check if sentinel is within the container
  if (container && !container.contains(sentinel)) {
    console.warn('[BROWSE-ALL-FILES] WARNING: Sentinel is NOT a child of the scroll container!')
  }

  intersectionObserver = new IntersectionObserver((entries) => {
    console.log('[BROWSE-ALL-FILES] IntersectionObserver callback fired: entries.length=', entries.length)
    entries.forEach((entry) => {
      console.log('[BROWSE-ALL-FILES] Entry details: isIntersecting=', entry.isIntersecting, 'intersectionRatio=', entry.intersectionRatio, 'browseHasMore=', browseHasMore.value, 'browseLoading=', browseLoading.value)
      if (entry.isIntersecting && browseHasMore.value && !browseLoading.value) {
        console.log('[BROWSE-ALL-FILES] Sentinel visible, triggering fetchBrowseFiles(true)')
        fetchBrowseFiles(true)
      } else {
        console.log('[BROWSE-ALL-FILES] Sentinel NOT triggering: isIntersecting=', entry.isIntersecting, 'hasMore=', browseHasMore.value, 'loading=', browseLoading.value)
      }
    })
  }, { root: browseContainerRef.value, threshold: 0.1 })

  intersectionObserver.observe(sentinel)
  console.log('[BROWSE-ALL-FILES] IntersectionObserver now observing sentinel, root=', browseContainerRef.value)
}

function setupBrowseAllScroll() {
  console.log('[BROWSE-ALL-FILES] setupBrowseAllScroll called')
  nextTick(() => {
    const container = browseContainerRef.value
    console.log('[BROWSE-ALL-FILES] setupBrowseAllScroll nextTick: container=', container)
    if (container) {
      // Remove old listener if any
      if (scrollCleanup) {
        console.log('[BROWSE-ALL-FILES] Removing old scroll listener')
        scrollCleanup()
        scrollCleanup = null
      }
      console.log('[BROWSE-ALL-FILES] Adding scroll listener to container')
      container.addEventListener('scroll', handleScroll, { passive: true })
      scrollCleanup = () => container.removeEventListener('scroll', handleScroll)
    } else {
      console.warn('[BROWSE-ALL-FILES] WARNING: browseContainerRef.value is null in nextTick!')
    }
    setupIntersectionObserver()
  })
}

function teardownBrowseAllScroll() {
  console.log('[infinite-scroll] Tearing down Browse All scroll listeners')
  if (scrollCleanup) {
    scrollCleanup()
    scrollCleanup = null
  }
  if (intersectionObserver) {
    intersectionObserver.disconnect()
    intersectionObserver = null
  }
}

function scrollToTop() {
  const container = browseContainerRef.value
  if (container) {
    container.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

onMounted(async () => {
  await fetchShops()
  document.addEventListener('click', handleDocumentClick)
  // Set up semantic search scroll listener
  nextTick(() => {
    const container = semanticSearchContainerRef.value
    if (container) {
      container.addEventListener('scroll', handleSemanticScroll, { passive: true })
      semanticScrollCleanup = () => container.removeEventListener('scroll', handleSemanticScroll)
    }
  })
})

onUnmounted(() => {
  document.removeEventListener('click', handleDocumentClick)
  teardownBrowseAllScroll()
  if (semanticScrollCleanup) {
    semanticScrollCleanup()
    semanticScrollCleanup = null
  }
})

// Watch for mode changes to set up/teardown scroll listeners
watch(isBrowseAllMode, (isActive) => {
  if (isActive) {
    setupBrowseAllScroll()
  } else {
    teardownBrowseAllScroll()
  }
}, { immediate: false })

definePageMeta({ layout: 'default' })
useHead({ title: 'Files - Art Management' })
</script>

<template>
  <div class="p-6 max-w-[1440px] mx-auto">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Files</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Search, browse, and link files to your shops</p>
    </div>

    <!-- Mode Switcher -->
    <div class="mb-6">
      <div class="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800">
        <button
          v-for="mode in modes"
          :key="mode.value"
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors',
            searchMode === mode.value
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          ]"
          @click="switchMode(mode.value)"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>

    <!-- ==================== SEARCH MODES (Semantic + Name) ==================== -->
    <div v-if="isSearchMode" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <!-- Back to Top Button -->
      <button
        v-show="searchMode === 'semantic' && showSemanticBackToTop && currentResults.length > 0"
        @click="scrollToSemanticTop"
        class="absolute bottom-4 right-4 z-30 p-2.5 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-all hover:scale-110 flex items-center justify-center"
        title="Back to top"
      >
        <SortAsc class="w-5 h-5" />
      </button>

      <!-- Search Input -->
      <div class="mb-6 flex gap-2">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            v-model="searchQuery"
            :placeholder="searchMode === 'semantic' ? 'Search with natural language... (e.g., green landscape painting)' : 'Search by filename or display name...'"
            class="w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @keyup.enter="handleSearchSubmit"
          />
        </div>
        <button
          @click="handleSearchSubmit"
          :disabled="searchLoading || !searchQuery.trim()"
          class="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="searchLoading" class="w-4 h-4 animate-spin" />
          <Search v-else class="w-4 h-4" />
          {{ searchLoading ? 'Searching...' : 'Search' }}
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
      <div v-if="ragQueryTimeMs > 0 && searchMode === 'semantic'" class="mb-4 text-sm text-gray-500 dark:text-gray-400">
        Found {{ ragTotalMatching }} matching results
      </div>

      <!-- Error Message -->
      <div v-if="searchError" class="mb-4 p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-3">
        <X class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
        <div>
          <p class="text-red-800 dark:text-red-200 font-medium">{{ searchError }}</p>
          <p v-if="searchError.includes('RAG service')" class="text-red-600 dark:text-red-400 text-sm mt-1">Make sure the RAG service is running on port 8079</p>
        </div>
      </div>

      <!-- No Matches Above Threshold Notice (semantic only) -->
      <div v-if="searchMode === 'semantic' && !searchLoading && ragSearchQuery && ragTotalMatching === 0 && !searchError" class="mb-4 p-4 bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg flex items-start gap-3">
        <AlertCircle class="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p class="text-amber-800 dark:text-amber-200 font-medium">No files matched your search description</p>
          <p class="text-amber-600 dark:text-amber-400 text-sm mt-1">Try rephrasing your query, using simpler terms, or describing visual characteristics (e.g., "abstract geometric pattern", "soft pastel landscape").</p>
        </div>
      </div>

      <!-- Scrollable Container for Semantic Search Results -->
      <div
        ref="semanticSearchContainerRef"
        class="max-h-[calc(90vh-14rem)] overflow-y-auto flex flex-col min-h-full"
        :class="{ 'pb-16': currentResults.length > 0 }"
      >
        <!-- Results Grid + Infinite Scroll Controls -->
        <div v-if="currentResults.length > 0" class="space-y-4">
          <!-- Results Grid -->
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-4 w-full">
            <div
              v-for="(result, index) in currentResults"
              :key="index"
              class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-pointer relative"
            >
              <!-- Image -->
              <div class="aspect-square bg-gray-100 dark:bg-gray-900 relative overflow-hidden">
                <img
                  :src="getPreviewUrl(getFileId(result), 540)"
                  :alt="getFilename(result)"
                  class="w-full h-full object-cover transition-transform group-hover:scale-105"
                  loading="lazy"
                  @error="e => (e.target as HTMLImageElement).style.display = 'none'"
                />
                <!-- Similarity Badge (semantic only) -->
                <div v-if="'similarity' in result" class="absolute top-2 right-2 px-2 py-1 bg-black/70 text-white text-xs rounded-full">
                  {{ formatSimilarity((result as SearchResult).similarity) }}
                </div>
                <!-- Enlarge Icon -->
                <button
                  class="absolute top-2 left-2 z-10 p-1.5 rounded-md bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                  @click.stop.prevent="openPreviewModal(getFileId(result), getFilename(result))"
                >
                  <Maximize2 class="w-3.5 h-3.5" />
                </button>
                <!-- Link Button (bottom-right, always visible on hover) -->
                <button
                  class="absolute bottom-2 right-2 z-20 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-700 flex items-center gap-1.5 shadow-lg"
                  @click.stop="openLinkMenu(result)"
                >
                  <ChevronRight class="w-3.5 h-3.5" />
                  Link
                </button>
              </div>
              <!-- File Info -->
              <div class="p-2">
                <p class="text-sm text-gray-900 dark:text-gray-100 truncate" :title="getFilename(result)">
                  {{ getFilename(result) }}
                </p>
                <p v-if="'displayName' in result && (result as any).displayName" class="text-[10px] text-gray-500 dark:text-gray-400 truncate">
                  {{ (result as any).displayName }}
                </p>
              </div>
            </div>
          </div>

          <!-- Bottom section: Loading spinner, sentinel, and Load More button -->
          <div class="flex flex-col items-center gap-4 py-4">
            <!-- Infinite Scroll Loading Spinner (between pages for semantic search) -->
            <div v-if="ragIsLoadingMore" class="text-center py-2">
              <Loader2 class="w-6 h-6 text-gray-400 mx-auto animate-spin" />
              <p class="text-gray-500 dark:text-gray-400 text-sm mt-2">Loading more results...</p>
            </div>

            <!-- Sentinel for Intersection Observer (infinite scroll trigger) - hidden visually -->
            <div v-if="searchMode === 'semantic' && ragHasMore" ref="semanticSentinelRef" class="w-full h-px" />

            <!-- Load More Button (fallback for users without IntersectionObserver support) -->
            <div v-if="searchMode === 'semantic' && ragHasMore && !ragIsLoadingMore && !semanticInfiniteScrollActive" class="text-center w-full">
              <button
                @click="loadMoreSemanticResults"
                class="px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors flex items-center gap-2 mx-auto shadow-md"
              >
                <Loader2 v-if="ragIsLoadingMore" class="w-5 h-5 animate-spin" />
                <Search v-else class="w-5 h-5" />
                Load More Results
              </button>
            </div>
          </div>
        </div>

        <!-- Loading State (initial search) -->
        <div v-if="searchLoading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 w-full">
          <div v-for="i in 6" :key="i" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden animate-pulse">
            <div class="aspect-square bg-gray-200 dark:bg-gray-700" />
            <div class="p-2"><div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" /></div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="!searchLoading && searchQuery && !searchError && currentResults.length === 0 && ragTotalMatching === 0 && ragQueryTimeMs !== 0" class="text-center py-12">
          <ImageIcon class="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p class="text-gray-500 dark:text-gray-400 text-lg">No results found</p>
        </div>
      </div>

    </div>

    <!-- ==================== BROWSE ALL MODE ==================== -->
    <div v-else-if="isBrowseAllMode" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4 relative">
      <!-- Back to Top Button -->
      <button
        v-show="showBackToTop"
        @click="scrollToTop"
        class="absolute bottom-4 right-4 z-30 p-2.5 rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700 transition-all hover:scale-110 flex items-center justify-center"
        title="Back to top"
      >
        <SortAsc class="w-5 h-5" />
      </button>
      <!-- Toolbar: Filter + Sort -->
      <div class="mb-4 flex flex-col sm:flex-row gap-3">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            v-model="filterQuery"
            type="text"
            placeholder="Filter by filename..."
            class="w-full pl-10 pr-10 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
          <button v-if="filterQuery" @click="clearFilter" class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X class="w-4 h-4" />
          </button>
        </div>
        <div class="relative">
          <button @click.stop="toggleSortDropdown" class="flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm">
            <SortAsc v-if="sortOrder === 'asc'" class="w-4 h-4" />
            <SortDesc v-else class="w-4 h-4" />
            <span>{{ sortLabel }}</span>
          </button>
          <div v-if="isSortDropdownOpen" class="absolute right-0 mt-1 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50">
            <div class="p-2 border-b border-gray-200 dark:border-gray-700">
              <p class="text-xs text-gray-500 dark:text-gray-400 px-2 py-1">Sort by</p>
              <button @click="setSortBy('fileid'); closeSortDropdown()" :class="['w-full text-left px-2 py-1.5 text-sm rounded transition-colors', sortBy === 'fileid' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']">File ID</button>
              <button @click="setSortBy('name'); closeSortDropdown()" :class="['w-full text-left px-2 py-1.5 text-sm rounded transition-colors', sortBy === 'name' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']">Name</button>
            </div>
            <div class="p-2">
              <p class="text-xs text-gray-500 dark:text-gray-400 px-2 py-1">Order</p>
              <button @click="sortOrder = 'asc'; closeSortDropdown()" :class="['w-full text-left px-2 py-1.5 text-sm rounded transition-colors flex items-center gap-2', sortOrder === 'asc' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']">
                <SortAsc class="w-3 h-3" /> Ascending
              </button>
              <button @click="sortOrder = 'desc'; closeSortDropdown()" :class="['w-full text-left px-2 py-1.5 text-sm rounded transition-colors flex items-center gap-2', sortOrder === 'desc' ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700']">
                <SortDesc class="w-3 h-3" /> Descending
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Filter Info -->
      <div v-if="filterQuery" class="mb-3 flex items-center justify-between text-sm">
        <p class="text-gray-600 dark:text-gray-400">Showing <span class="font-medium text-gray-900 dark:text-gray-100">{{ filterCount }}</span> of {{ displayedFiles.length }} files <span class="text-gray-500 dark:text-gray-500">matching "{{ filterQuery }}"</span></p>
        <button @click="clearFilter" class="text-blue-600 dark:text-blue-400 hover:underline">Clear filter</button>
      </div>

      <!-- Scrollable Container -->
      <div
        ref="browseContainerRef"
        class="max-h-[calc(90vh-14rem)] overflow-y-auto flex flex-col min-h-full justify-between"
        :class="{ 'pt-4': filterQuery || browseLoading || filteredFiles.length > 0 }"
      >
        <!-- Loading State -->
        <div v-if="browseLoading && displayedFiles.length === 0" class="text-center py-12">
          <Loader2 class="w-12 h-12 text-gray-400 mx-auto mb-4 animate-spin" />
          <p class="text-gray-500 dark:text-gray-400">Loading files...</p>
        </div>

        <!-- Results Grid -->
        <div v-else-if="filteredFiles.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-4 w-full">
        <div
          v-for="file in filteredFiles"
          :key="file.fileId"
          class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-pointer relative"
        >
          <div class="aspect-square bg-gray-100 dark:bg-gray-900 relative overflow-hidden">
            <img
              :src="getPreviewUrl(file.fileId, 540)"
              :alt="file.filename"
              class="w-full h-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
              @error="e => (e.target as HTMLImageElement).style.display = 'none'"
            />
            <!-- Enlarge Icon (Top Left) -->
            <button
              class="absolute top-2 left-2 z-10 p-1.5 rounded-md bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
              @click.stop.prevent="openPreviewModal(file.fileId, file.filename)"
            >
              <Maximize2 class="w-3.5 h-3.5" />
            </button>
            <!-- Link Button (Bottom Right) -->
            <button
              class="absolute bottom-2 right-2 z-20 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-700 flex items-center gap-1.5 shadow-lg"
              @click.stop="openLinkMenu({ fileId: file.fileId, filename: file.filename } as LinkFileResult)"
            >
              <ChevronRight class="w-3.5 h-3.5" />
              Link
            </button>
          </div>
          <div class="p-2">
            <p class="text-sm text-gray-900 dark:text-gray-100 truncate" :title="file.filename">{{ file.filename }}</p>
          </div>
        </div>
      </div>

        <!-- No Filter Results -->
        <div v-if="filterQuery && displayedFiles.length > 0 && filteredFiles.length === 0" class="text-center py-12">
          <ImageIcon class="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p class="text-gray-500 dark:text-gray-400 text-lg">No matching files</p>
        </div>

        <!-- Loading Spinner (between pages) -->
        <div v-if="browseLoading && displayedFiles.length > 0" class="text-center py-6">
          <Loader2 class="w-6 h-6 text-gray-400 mx-auto animate-spin" />
        </div>

        <!-- Sentinel for Intersection Observer (infinite scroll trigger) -->
        <div ref="sentinelRef" class="h-4" />

        <!-- Empty State (only when no files loaded at all) -->
        <div v-if="!browseLoading && displayedFiles.length === 0 && !filterQuery" class="text-center py-12">
          <ImageIcon class="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p class="text-gray-500 dark:text-gray-400 text-lg">No files found</p>
        </div>
      </div>
    </div>

    <!-- ==================== REVERSE SEARCH MODE ==================== -->
    <div v-else-if="isReverseMode" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <!-- Hash Method Selection -->
      <div class="flex items-center gap-4 mb-6">
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Hash Method:</label>
        <select v-model="selectedHashMethod" class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100">
          <option value="whash">Whitened Hash</option>
          <option value="ahash">Average Hash</option>
          <option value="phash">Phase Hash</option>
        </select>
      </div>

      <!-- Upload Area (shown when no image uploaded) -->
      <div
        v-if="!uploadedImage"
        class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-12 text-center cursor-pointer hover:border-blue-500 dark:hover:border-blue-400 transition-colors"
        @click="triggerFileInput()"
        @dragover.prevent
        @drop="handleDrop"
      >
        <Upload class="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p class="text-gray-600 dark:text-gray-400 mb-2">Drag and drop an image here, or click to select</p>
        <p class="text-sm text-gray-500 dark:text-gray-500">Supports JPG, PNG, WEBP</p>
        <input ref="fileInputRef" type="file" accept="image/jpeg,image/png,image/webp" class="hidden" @change="handleImageUpload" />
      </div>

      <!-- Uploaded Image + Results Layout -->
      <div v-else class="mt-6">
        <!-- 2x1 Grid: Uploaded Image | Best Match -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <!-- Uploaded Image -->
          <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div class="bg-gray-50 dark:bg-gray-800 p-3 border-b border-gray-200 dark:border-gray-700">
              <p class="text-sm font-medium text-gray-700 dark:text-gray-300">Uploaded Image</p>
            </div>
            <div class="p-4 flex items-center justify-center bg-gray-100 dark:bg-gray-800">
              <div class="relative">
                <img :src="uploadedImagePreview || ''" :alt="uploadedImage?.name || 'Uploaded image'" class="max-w-full max-h-64 object-contain rounded" />
                <button
                  class="absolute top-2 right-2 p-1.5 rounded-md bg-black/50 text-white hover:bg-black/70"
                  @click.stop.prevent="openPreviewModal(0, uploadedImage?.name || 'Uploaded')"
                  title="View enlarged"
                >
                  <Maximize2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div class="p-3 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ uploadedImage?.name }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">{{ uploadedImage ? (uploadedImage.size / 1024 / 1024).toFixed(2) : '0' }} MB</p>
              </div>
              <button v-if="!uploadLoading" @click="uploadedImage = null" class="p-2 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors">
                <X class="w-4 h-4 text-gray-500" />
              </button>
            </div>
          </div>

          <!-- Best Match (Lowest Distance) -->
          <div v-if="bestReverseMatch" class="rounded-lg border border-blue-300 dark:border-blue-600 overflow-hidden">
            <div class="bg-blue-50 dark:bg-blue-950/30 p-3 border-b border-blue-200 dark:border-blue-800">
              <p class="text-sm font-medium text-blue-700 dark:text-blue-300">Best Match</p>
            </div>
            <div class="p-4 cursor-pointer" @click="openPreviewModal(bestReverseMatch.fileId, bestReverseMatch.filename)">
              <div class="relative aspect-square bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
                <img
                  :src="getPreviewUrl(bestReverseMatch.fileId, 540)"
                  :alt="bestReverseMatch.filename"
                  class="w-full h-full object-cover"
                  @error="e => (e.target as HTMLImageElement).style.display = 'none'"
                />
                <button
                  class="absolute top-2 right-2 p-1.5 rounded-md bg-black/50 text-white hover:bg-black/70"
                  @click.stop.prevent="openPreviewModal(bestReverseMatch.fileId, bestReverseMatch.filename)"
                >
                  <Maximize2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <div class="p-3 bg-blue-50 dark:bg-blue-950/30 border-t border-blue-200 dark:border-blue-800">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ bestReverseMatch.filename }}</p>
              <p v-if="bestReverseMatch.combinedDistance !== undefined" class="text-xs text-blue-600 dark:text-blue-400 mt-1">
                Distance: {{ formatDistance(bestReverseMatch.combinedDistance) }}
              </p>
              <button
                @click="openLinkMenu(bestReverseMatch)"
                class="mt-2 w-full px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
              >
                <ChevronRight class="w-4 h-4" />
                Link to Shop
              </button>
            </div>
          </div>

          <!-- Placeholder when no results -->
          <div v-else class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex items-center justify-center bg-gray-50 dark:bg-gray-800">
            <p class="text-gray-400 dark:text-gray-500">Waiting for search results...</p>
          </div>
        </div>

        <!-- Upload/Search Button -->
        <button
          v-if="!uploadLoading && !reverseSearchResults.length"
          @click="uploadedImage && performReverseSearch(uploadedImage)"
          class="w-full px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          <Eye class="w-4 h-4" />
          Search for Similar Images
        </button>

        <!-- Loading State -->
        <div v-if="uploadLoading || searchLoading" class="p-12 text-center">
          <Loader2 class="w-8 h-8 animate-spin mx-auto text-gray-400" />
          <p class="text-gray-500 dark:text-gray-400 mt-2">Processing image...</p>
        </div>

        <!-- 3x3 Grid: Other Results -->
        <div v-else-if="otherReverseMatches.length > 0" class="mt-6">
          <div class="flex items-center justify-between mb-4">
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Found {{ reverseSearchResults.length }} similar images
              <span v-if="exceedsLimit" class="text-amber-600 dark:text-amber-400">(limited to 10)</span>
            </p>
            <button @click="reverseSearchResults = []; uploadedImage = null" class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">Clear</button>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 w-full">
            <div
              v-for="file in otherReverseMatches"
              :key="file.fileId"
              class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-pointer relative"
            >
              <div class="aspect-square bg-gray-100 dark:bg-gray-900 relative overflow-hidden">
                <img
                  :src="getPreviewUrl(file.fileId, 540)"
                  :alt="file.filename"
                  class="w-full h-full object-cover transition-transform group-hover:scale-105"
                  loading="lazy"
                  @error="e => (e.target as HTMLImageElement).style.display = 'none'"
                />
                <!-- Enlarge Icon (Top Left) -->
                <button
                  class="absolute top-2 left-2 z-10 p-1.5 rounded-md bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                  @click.stop.prevent="openPreviewModal(file.fileId, file.filename)"
                >
                  <Maximize2 class="w-3.5 h-3.5" />
                </button>
                <!-- Distance Badge (Top Right) -->
                <div v-if="file.combinedDistance !== undefined" class="absolute top-2 right-2 px-2 py-1 bg-black/70 text-white text-xs rounded-full">
                  dist: {{ formatDistance(file.combinedDistance) }}
                </div>
                <!-- Link Button (Bottom Right) -->
                <button
                  class="absolute bottom-2 right-2 z-20 px-3 py-1.5 rounded-lg bg-blue-600 text-white text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-700 flex items-center gap-1.5 shadow-lg"
                  @click.stop="openLinkMenu(file)"
                >
                  <ChevronRight class="w-3.5 h-3.5" />
                  Link
                </button>
              </div>
              <div class="p-2">
                <p class="text-sm text-gray-900 dark:text-gray-100 truncate" :title="file.filename">{{ file.filename }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upload Error -->
      <div v-if="uploadError" class="p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 mt-4">
        <p class="text-red-600 dark:text-red-400 text-sm">{{ uploadError }}</p>
      </div>
    </div>

    <!-- ==================== LINK SIDEBAR MENU ==================== -->
    <Teleport to="body">
      <Transition name="menu">
        <div v-if="showLinkMenu" class="fixed inset-0 z-50 flex justify-end" @click.self="closeLinkMenu">
          <div class="absolute inset-0 bg-black/30" @click="closeLinkMenu"></div>
          <div class="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-xl border-l border-gray-200 dark:border-gray-700 flex flex-col">
            <!-- Header -->
            <div class="p-6 border-b border-gray-200 dark:border-gray-700">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Link File</h2>
                <button @click="closeLinkMenu" class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors">
                  <X class="w-5 h-5" />
                </button>
              </div>
              <!-- Selected File Preview -->
              <div v-if="selectedFile" class="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-800">
                <img
                  :src="selectedFile.fileId ? getPreviewUrl(selectedFile.fileId, 64) : ''"
                  :alt="selectedFile.filename"
                  class="w-16 h-16 rounded object-cover"
                  @error="(e) => { (e.target as HTMLImageElement).style.display = 'none' }"
                />
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ selectedFile.filename }}</p>
                  <p v-if="(selectedFile as any).displayName" class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ (selectedFile as any).displayName }}</p>
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
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Shop <span class="text-red-500">*</span></label>
                <select v-model="selectedShopId" @change="onShopChange(selectedShopId!)" class="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500">
                  <option :value="null" disabled>Select a shop</option>
                  <option v-for="shop in shops" :key="shop.shop_id" :value="shop.shop_id">{{ shop.shop_name }}</option>
                </select>
              </div>

              <!-- Account Selection -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Account <span class="text-red-500">*</span></label>
                <select v-model="selectedAccountId" @change="onAccountChange(selectedAccountId!)" :disabled="!selectedShopId" class="w-full px-3 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed">
                  <option :value="null" disabled>Select an account</option>
                  <option v-for="account in accounts" :key="account.account_id" :value="account.account_id">{{ account.account_name }}</option>
                </select>
              </div>

              <!-- Display Names (Tag-style Input) -->
              <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Display Names</label>
                <div class="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
                  <!-- Tags -->
                  <div class="flex flex-wrap items-center gap-1.5 p-2">
                    <span
                      v-for="(name, index) in displayNames"
                      :key="index"
                      class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 text-sm font-medium"
                    >
                      <span class="truncate max-w-[150px]">{{ name }}</span>
                      <button
                        @click="removeDisplayName(index)"
                        class="flex items-center justify-center rounded-full hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
                      >
                        <X class="w-3 h-3" />
                      </button>
                    </span>
                    <!-- Input for new tags -->
                    <input
                      v-model="displayNameInput"
                      @keydown="handleDisplayNameKeydown"
                      type="text"
                      placeholder="Type and press Enter to add..."
                      class="flex-1 min-w-[120px] bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 text-sm placeholder-gray-400"
                    />
                  </div>
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Press Enter or comma to add a display name</p>
              </div>

              <!-- Published Toggle -->
              <div class="mb-4">
                <label class="flex items-center gap-3 cursor-pointer group">
                  <div class="relative">
                    <input v-model="published" type="checkbox" class="sr-only" />
                    <div :class="['w-10 h-6 rounded-full transition-colors', published ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600']"></div>
                    <div :class="['absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform shadow', published ? 'translate-x-4' : 'translate-x-0']"></div>
                  </div>
                  <div>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100">Published in {{ selectedShopName }}?</span>
                    <p class="text-xs text-gray-500 dark:text-gray-400">Make this file available for purchase</p>
                  </div>
                </label>
              </div>
            </div>

            <!-- Footer -->
            <div class="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
              <button @click="closeLinkMenu" class="flex-1 px-4 py-2.5 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">Cancel</button>
              <button @click="handleLinkSubmit" :disabled="!selectedShopId || !selectedAccountId" class="flex-1 px-4 py-2.5 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">Link File</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Image Preview Modal -->
    <ImagePreviewModal :state="previewState" :close="closePreview" :navigate="navigatePreview" />
  </div>
</template>

<style scoped>
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
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
.dark ::-webkit-scrollbar-thumb { background: #4b5563; }
</style>
