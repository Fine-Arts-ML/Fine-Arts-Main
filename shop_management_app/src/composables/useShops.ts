import type { Shop } from '~/types'

export const useShops = () => {
  const shops = ref<Shop[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const fetchShops = async () => {
    loading.value = true
    error.value = null
    try {
      shops.value = await $fetch('/api/shops')
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch shops'
    } finally {
      loading.value = false
    }
  }

  const createShop = async (name: string) => {
    try {
      const newShop = await $fetch('/api/shops', {
        method: 'POST',
        body: { shopName: name },
      })
      shops.value.push(newShop)
      return newShop
    } catch (e: any) {
      error.value = e.message || 'Failed to create shop'
      throw e
    }
  }

  onMounted(() => {
    fetchShops()
  })

  return { shops, loading, error, fetchShops, createShop }
}