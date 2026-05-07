import { ref, onMounted, onUnmounted, watch } from 'vue'
import type {
  LinkFileResult,
  HashMethod,
  SearchMode,
  HashResult,
} from '~/types/linkFiles'
import type { Shop } from '~/types/shop'
import type { Account } from '~/types/account'

export const useLinkFiles = () => {
  // State
  const searchMode = ref<SearchMode>('filename')
  const searchQuery = ref('')
  const searchResults = ref<LinkFileResult[]>([])
  const showLinkMenu = ref(false)
  const selectedFile = ref<LinkFileResult | null>(null)
  const selectedShopId = ref<number | null>(null)
  const selectedAccountId = ref<number | null>(null)
  const shops = ref<Shop[]>([])
  const accounts = ref<Account[]>([])
  const uploadedImage = ref<File | null>(null)
  const selectedHashMethod = ref<HashMethod>('whash')
  const exceedsLimit = ref(false)
  const loading = ref(false)
  const searchLoading = ref(false)
  const uploadLoading = ref(false)
  const uploadError = ref<string | null>(null)
  const searchError = ref<string | null>(null)
  const published = ref(false) // Published flag for link-to-shop

  // Fetch shops on mount
  async function fetchShops() {
    try {
      shops.value = await $fetch('/api/shops')
    } catch (e: any) {
      console.error('Failed to fetch shops:', e)
    }
  }

  // Fetch accounts for a shop
  async function fetchAccounts(shopId: number) {
    try {
      accounts.value = await $fetch(`/api/shops/${shopId}/accounts`)
    } catch (e: any) {
      console.error('Failed to fetch accounts:', e)
    }
  }

  // Mode 1: Search by filename or display name
  async function searchByFilename(query: string) {
    if (!query || query.trim().length === 0) return

    searchLoading.value = true
    searchError.value = null
    exceedsLimit.value = false

    try {
      const params = new URLSearchParams({
        query: query.trim(),
        limit: '10',
        previewSize: '540',
      })
      const results = await $fetch(`/api/files/search-by-name?${params}`)
      searchResults.value = results
      exceedsLimit.value = results.length >= 10
    } catch (e: any) {
      console.error('Search failed:', e)
      searchError.value = e.statusMessage || 'Search failed. Please try again.'
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }

  // Mode 2: Reverse image search
  async function reverseSearch(imageFile: File) {
    uploadLoading.value = true
    uploadError.value = null
    searchLoading.value = true
    searchError.value = null
    exceedsLimit.value = false
    uploadedImage.value = imageFile

    try {
      const formData = new FormData()
      formData.append('image', imageFile)
      formData.append('hashMethod', selectedHashMethod.value)

      const results = await $fetch('/api/files/reverse-search', {
        method: 'POST',
        body: formData,
      })
      searchResults.value = results
      exceedsLimit.value = results.length >= 10
    } catch (e: any) {
      console.error('Reverse search failed:', e)
      uploadError.value = e.statusMessage || 'Reverse search failed. Please try again.'
      searchError.value = uploadError.value
      searchResults.value = []
    } finally {
      uploadLoading.value = false
      searchLoading.value = false
    }
  }

  // Link file to shop and account
  async function linkFileToShopAccount(fileId: number, shopId: number, accountId: number, publishedFlag = false) {
    try {
      await $fetch('/api/files/link-to-shop-account', {
        method: 'POST',
        body: { fileId, shopId, accountId, published: publishedFlag },
      })
      return true
    } catch (e: any) {
      console.error('Failed to link file:', e)
      throw e
    }
  }

  // Open link menu
  function openLinkMenu(file: LinkFileResult) {
    selectedFile.value = file
    showLinkMenu.value = true
    // Reset selections
    selectedShopId.value = null
    selectedAccountId.value = null
    accounts.value = []
    // Fetch accounts if we have a shop selected
    if (selectedShopId.value) {
      fetchAccounts(selectedShopId.value)
    }
  }

  // Close link menu
  function closeLinkMenu() {
    showLinkMenu.value = false
    selectedFile.value = null
    published.value = false // Reset published flag
  }

  // Handle shop selection in link menu
  function onShopChange(shopId: number) {
    selectedShopId.value = shopId
    selectedAccountId.value = null
    fetchAccounts(shopId)
  }

  // Handle account selection in link menu
  function onAccountChange(accountId: number) {
    selectedAccountId.value = accountId
  }

  // Handle image upload for reverse search
  function handleImageUpload(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    if (file) {
      reverseSearch(file)
    }
  }

  // Handle drag and drop
  function handleDrop(event: DragEvent) {
    event.preventDefault()
    const file = event.dataTransfer?.files[0]
    if (file && file.type.startsWith('image/')) {
      reverseSearch(file)
    }
  }

  function handleDragOver(event: DragEvent) {
    event.preventDefault()
  }

  // Switch search mode
  function switchMode(mode: SearchMode) {
    searchMode.value = mode
    searchResults.value = []
    searchQuery.value = ''
    uploadedImage.value = null
    searchError.value = null
    uploadError.value = null
    exceedsLimit.value = false
  }

  // Clear results
  function clearResults() {
    searchResults.value = []
    searchQuery.value = ''
    uploadedImage.value = null
    searchError.value = null
    uploadError.value = null
    exceedsLimit.value = false
  }

  // Watch for hash method changes and re-run reverse search if we have an uploaded image and results
  watch(selectedHashMethod, (newMethod, oldMethod) => {
    if (oldMethod !== undefined && uploadedImage.value && searchResults.value.length > 0) {
      // Re-run reverse search with the new hash method
      reverseSearch(uploadedImage.value)
    }
  })

  onMounted(() => {
    fetchShops()
  })

  return {
    // State
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
    loading,
    searchLoading,
    uploadLoading,
    uploadError,
    searchError,
    published,

    // Actions
    fetchShops,
    fetchAccounts,
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
  }
}
