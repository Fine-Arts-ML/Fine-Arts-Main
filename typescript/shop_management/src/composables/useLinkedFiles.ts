import { ref, onUnmounted } from 'vue'
import { $fetch } from 'ofetch'
import type { LinkedFileResult, ShopAccountWithFileCount } from '~/types/linkedFile'
import type { Shop } from '~/types/shop'

export const useLinkedFiles = () => {
  // State
  const selectedShop = ref<Shop | null>(null)
  const selectedAccount = ref<{ accountId: number; accountName: string } | null>(null)
  const searchQuery = ref('')
  const publishedFilter = ref<'all' | 'true' | 'false'>('all')
  const linkedFiles = ref<LinkedFileResult[]>([])
  const shopAccounts = ref<ShopAccountWithFileCount[]>([])
  const loading = ref(false)
  const searchLoading = ref(false)
  const offset = ref(0)
  const hasMore = ref(true)
  const visibleRows = ref(15) // default for ~1200px viewport

  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let abortController: AbortController | null = null
  let resizeObserver: ResizeObserver | null = null

  // Calculate visible rows based on viewport height
  function calculateVisibleRows(availableHeight: number) {
    const rowHeight = 80 // 64px thumbnail + padding + text
    const calculated = Math.floor(availableHeight / rowHeight)
    visibleRows.value = Math.min(Math.max(calculated, 10), 20)
  }

  // Set up ResizeObserver for viewport-based sizing
  function setupResizeObserver(element: HTMLElement | null) {
    if (!element) return

    if (resizeObserver) {
      resizeObserver.disconnect()
    }

    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const height = entry.contentRect.height
        if (height > 0) {
          calculateVisibleRows(height)
        }
      }
    })

    resizeObserver.observe(element)
  }

  // Clean up on unmount
  onUnmounted(() => {
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
    cancelPendingRequests()
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
  })

  // Cancel pending requests
  function cancelPendingRequests() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }

  // Fetch accounts for a shop
  async function fetchAccounts(shopId: number) {
    loading.value = true
    try {
      shopAccounts.value = await $fetch(`/api/shops/${shopId}/accounts-with-files`)
    } catch (e: any) {
      console.error('Failed to fetch shop accounts:', e)
    } finally {
      loading.value = false
    }
  }

  // Fetch files based on current selection state
  async function fetchFiles(append = false) {
    if (!selectedShop.value) return

    cancelPendingRequests()
    abortController = new AbortController()

    const params: Record<string, string> = {
      limit: String(visibleRows.value),
      offset: String(offset.value),
      previewSize: '64', // Thumbnail size for preview URLs
    }

    if (selectedAccount.value) {
      params.accountId = String(selectedAccount.value.accountId)
    }

    if (publishedFilter.value !== 'all') {
      params.published = publishedFilter.value
    }

    if (searchQuery.value.trim()) {
      params.query = searchQuery.value.trim()
    }

    const url = `/api/shops/${selectedShop.value.shop_id}/linked-files-search?${new URLSearchParams(Object.entries(params)).toString()}`
    
    console.log('[useLinkedFiles] Fetching files:', url)

    try {
      const rawFiles = await $fetch(url)
      console.log('[useLinkedFiles] Received files:', rawFiles?.length || 0)

      // Transform API response to match LinkedFileResult type
      // The API returns accountNames as a PostgreSQL array, transform to proper format
      const transformedFiles = (rawFiles || []).map((file: any) => ({
        fileId: file.fileId,
        filename: file.filename,
        previewUrl: file.previewUrl,
        displayName: file.displayName,
        published: file.published ?? false,
        accountId: file.accountIds?.[0] ?? 0,
        accountName: file.accountNames?.[0] ?? '',
        accountNames: file.accountNames ?? [],
        accountIds: (file.accountIds || []).map((id: any) => Number(id)),
      }))

      if (append) {
        linkedFiles.value = [...linkedFiles.value, ...transformedFiles]
      } else {
        linkedFiles.value = transformedFiles
      }

      hasMore.value = (transformedFiles?.length || 0) >= visibleRows.value
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error('[useLinkedFiles] Failed to fetch linked files:', e.message)
      }
      if (append) {
        // Don't clear files on append error
      } else {
        linkedFiles.value = []
      }
    } finally {
      abortController = null
    }
  }

  // Select a shop
  async function selectShop(shop: Shop) {
    // If clicking the same shop, stay in shop view
    if (selectedShop.value?.shop_id === shop.shop_id) {
      return
    }

    // New shop selected - reset state
    selectedShop.value = shop
    selectedAccount.value = null
    publishedFilter.value = 'all'
    searchQuery.value = ''
    offset.value = 0
    hasMore.value = true

    await Promise.all([
      fetchAccounts(shop.shop_id),
      fetchFiles(false),
    ])
  }

  // Select an account (drill down)
  async function selectAccount(account: { accountId: number | bigint; accountName: string }) {
    const accountNum = Number(account.accountId)
    selectedAccount.value = {
      accountId: accountNum,
      accountName: account.accountName,
    }
    searchQuery.value = ''
    offset.value = 0
    hasMore.value = true

    await fetchFiles(false)
  }

  // Click on shop name to go back to shop list
  function goBackToShopList() {
    selectedShop.value = null
    selectedAccount.value = null
    publishedFilter.value = 'all'
    searchQuery.value = ''
    linkedFiles.value = []
    shopAccounts.value = []
    offset.value = 0
    hasMore.value = true
    cancelPendingRequests()
  }

  // Click on account to go back to shop view
  function goBackToShopView() {
    if (!selectedShop.value) return

    selectedAccount.value = null
    publishedFilter.value = 'all'
    searchQuery.value = ''
    offset.value = 0
    hasMore.value = true

    fetchFiles(false)
  }

  // Perform search (debounced)
  function performSearch(query: string) {
    searchQuery.value = query

    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }

    debounceTimer = setTimeout(() => {
      if (selectedShop.value) {
        offset.value = 0
        hasMore.value = true
        fetchFiles(false)
      }
    }, 300)
  }

  // Set published filter
  async function setPublishedFilter(filter: 'all' | 'true' | 'false') {
    publishedFilter.value = filter
    offset.value = 0
    hasMore.value = true
    await fetchFiles()
  }

  // Load more files
  async function loadMore() {
    if (!hasMore.value || loading.value) return

    loading.value = true
    try {
      offset.value += visibleRows.value
      await fetchFiles(true)
    } finally {
      loading.value = false
    }
  }

  // Unlink a file from the current shop and optionally an account
  async function unlinkFile(fileId: number, accountId?: number) {
    if (!selectedShop.value) return false

    try {
      await $fetch('/api/files/unlink', {
        method: 'POST',
        body: {
          fileId,
          shopId: selectedShop.value.shop_id,
          accountId,
        },
      })

      // Remove file from the list
      linkedFiles.value = linkedFiles.value.filter(
        f => Number(f.fileId) !== fileId
      )

      return true
    } catch (e: any) {
      console.error('[useLinkedFiles] Failed to unlink file:', e)
      return false
    }
  }

  // Toggle published status for a file
  async function togglePublished(fileId: number, newPublished: boolean) {
    if (!selectedShop.value) return false

    try {
      await $fetch('/api/files/published', {
        method: 'PUT',
        body: {
          fileId,
          shopId: selectedShop.value.shop_id,
          published: newPublished,
        },
      })

      // Update local state - replace the object to trigger Vue reactivity
      const fileIndex = linkedFiles.value.findIndex(f => Number(f.fileId) === fileId)
      if (fileIndex !== -1) {
        const file = linkedFiles.value[fileIndex]
        linkedFiles.value[fileIndex] = {
          fileId: file.fileId,
          filename: file.filename,
          previewUrl: file.previewUrl,
          displayName: file.displayName,
          published: newPublished,
          accountId: file.accountId,
          accountName: file.accountName,
          accountNames: file.accountNames,
        }
      }

      return true
    } catch (e: any) {
      console.error('[useLinkedFiles] Failed to toggle published:', e)
      return false
    }
  }

  // Clear all selections
  function clearSelection() {
    goBackToShopList()
  }

  return {
    // State
    selectedShop,
    selectedAccount,
    publishedFilter,
    searchQuery,
    linkedFiles,
    shopAccounts,
    loading,
    searchLoading,
    offset,
    hasMore,
    visibleRows,

    // Actions
    selectShop,
    selectAccount,
    goBackToShopList,
    goBackToShopView,
    performSearch,
    setPublishedFilter,
    togglePublished,
    loadMore,
    unlinkFile,
    clearSelection,
    calculateVisibleRows,
    setupResizeObserver,
  }
}
