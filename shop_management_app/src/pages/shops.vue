<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  CollapsibleRoot,
  CollapsibleTrigger,
  CollapsibleContent,
} from 'radix-vue'
import { ChevronDown, Pencil, User, Trash2, Plus } from 'lucide-vue-next'
import { useShops } from '~/composables/useShops'

// Type for shop accounts map
interface ShopAccountsMap {
  [key: number]: { account_id: number; account_name: string }[]
}

// Use the shops composable
const { shops, loading: shopsLoading, error: shopsError, fetchShops, createShop } = useShops()

// Tab state
const activeTab = ref('shop-management')

// Expanded shops state
const expandedShops = ref<Set<number>>(new Set())

// Form state
const newShopName = ref('')
const newAccountName = ref('')

// Account management state
const accounts = ref<{ account_id: number; account_name: string; shop_id: number | null }[]>([])
const accountsLoading = ref(false)
const accountsError = ref<string | null>(null)

// Shop-specific account form state
const shopAccountName = ref<Record<number, string>>({})

// Loading states for operations
const addingShop = ref(false)
const addingAccount = ref<Record<number, boolean>>({})
const deletingShop = ref<Record<number, boolean>>({})
const deletingAccount = ref<Record<string, boolean>>({})

// Edit shop dialog state
const editingShop = ref<{ id: number; name: string } | null>(null)
const editingShopName = ref('')

// Edit account dialog state (Account Management tab)
const editingAccount = ref<{ id: number; name: string } | null>(null)
const editingAccountName = ref('')

// Link account dialog state
const linkingShopId = ref<number | null>(null)
const selectedAccountIds = ref<Set<number>>(new Set())

// Fetch accounts on mount
async function fetchAccounts() {
  accountsLoading.value = true
  accountsError.value = null
  try {
    const res = await $fetch<{ account_id: number; account_name: string; shop_count: number }[]>('/api/accounts')
    // Map to include shop_id (use shop_count to infer, or set null if unassigned)
    accounts.value = res.map(a => ({
      account_id: a.account_id,
      account_name: a.account_name,
      shop_id: a.shop_count > 0 ? 0 : null, // Will be updated when we have per-account shop info
    }))
  } catch (err: any) {
    accountsError.value = err.message || 'Failed to fetch accounts'
  } finally {
    accountsLoading.value = false
  }
}

// Toggle shop expansion
function toggleShop(shopId: number) {
  const next = new Set(expandedShops.value)
  if (next.has(shopId)) {
    next.delete(shopId)
  } else {
    next.add(shopId)
  }
  expandedShops.value = next
}

function isShopExpanded(shopId: number): boolean {
  return expandedShops.value.has(shopId)
}

// Add shop handler
async function handleAddShop() {
  const name = newShopName.value.trim()
  if (!name) return
  addingShop.value = true
  try {
    await createShop(name)
    newShopName.value = ''
    // Refresh shops list to show the newly created shop
    await fetchShops()
  } catch (err: any) {
    alert(err.message || 'Failed to create shop')
  } finally {
    addingShop.value = false
  }
}

// Mock accounts per shop (will be replaced with real data from API)
const shopAccounts = ref<ShopAccountsMap>({})

// Fetch accounts for a specific shop
async function fetchShopAccounts(shopId: number) {
  try {
    const res = await $fetch<{ account_id: number; account_name: string }[]>(`/api/shops/${shopId}/accounts`)
    shopAccounts.value[shopId] = res
  } catch (err: any) {
    console.error(`Failed to fetch accounts for shop ${shopId}:`, err)
    shopAccounts.value[shopId] = []
  }
}

// Add account to shop handler
async function handleAddAccount(shopId: number) {
  const name = newAccountName.value.trim()
  if (!name) return
  if (!addingAccount.value[shopId]) {
    addingAccount.value[shopId] = true
  }
  try {
    // First create the account, then link it to the shop
    const accountRes = await $fetch<{ account_id: number; account_name: string }>('/api/accounts', {
      method: 'POST',
      body: { accountName: name },
    })
    // Then link it to the shop
    await $fetch(`/api/shops/${shopId}/accounts`, {
      method: 'POST',
      body: { accountId: accountRes.account_id },
    })
    newAccountName.value = ''
    // Refresh shop accounts
    await fetchShopAccounts(shopId)
    // Refresh shops list to update account counts
    await fetchShops()
    // Refresh accounts list
    await fetchAccounts()
  } catch (err: any) {
    alert(err.message || 'Failed to add account')
  } finally {
    addingAccount.value[shopId] = false
  }
}

// Create standalone account (Account Management tab)
async function handleCreateAccount() {
  const name = newAccountName.value.trim()
  if (!name) return
  try {
    await $fetch('/api/accounts', {
      method: 'POST',
      body: { accountName: name },
    })
    newAccountName.value = ''
    await fetchAccounts()
  } catch (err: any) {
    alert(err.message || 'Failed to create account')
  }
}

// Delete shop handler
async function handleDeleteShop(shopId: number) {
  if (!confirm('Are you sure you want to delete this shop?')) return
  deletingShop.value[shopId] = true
  try {
    await $fetch(`/api/shops/${shopId}`, { method: 'DELETE' })
    expandedShops.value.delete(shopId)
    // Refresh shops list to reflect the deletion
    await fetchShops()
    // Refresh accounts list as well
    await fetchAccounts()
  } catch (err: any) {
    alert(err.message || 'Failed to delete shop')
  } finally {
    deletingShop.value[shopId] = false
  }
}

// Delete account handler (Shop Management tab - removing account from shop)
async function handleDeleteAccount(shopId: number, accountId: number) {
  const key = `${shopId}-${accountId}`
  deletingAccount.value[key] = true
  try {
    await $fetch(`/api/accounts/${accountId}`, { method: 'DELETE' })
    // Refresh shop accounts
    await fetchShopAccounts(shopId)
    // Refresh shops list to update account counts
    await fetchShops()
    // Refresh accounts list
    await fetchAccounts()
  } catch (err: any) {
    alert(err.message || 'Failed to delete account')
  } finally {
    deletingAccount.value[key] = false
  }
}

// Delete account handler (Account Management tab - full deletion with confirmation)
async function handleDeleteAccountFromManagement(accountId: number) {
  if (!confirm('Are you sure you want to delete this account? This will also remove all associated file links and shop connections.')) {
    return
  }
  const key = `management-${accountId}`
  deletingAccount.value[key] = true
  try {
    await $fetch(`/api/accounts/${accountId}`, { method: 'DELETE' })
    // Refresh accounts list
    await fetchAccounts()
    // Refresh shops list to update account counts
    await fetchShops()
  } catch (err: any) {
    alert(err.message || 'Failed to delete account')
  } finally {
    deletingAccount.value[key] = false
  }
}

// Helper to get accounts for a shop safely
function getShopAccounts(shopId: number): { account_id: number; account_name: string }[] {
  return shopAccounts.value[shopId] || []
}

// Fetch shop accounts when a shop is expanded
async function onShopExpanded(shopId: number) {
  if (!shopAccounts.value[shopId]) {
    await fetchShopAccounts(shopId)
  }
}

// Edit shop handlers
function openEditShopDialog(shop: { shop_id: number; shop_name: string }) {
  editingShop.value = { id: shop.shop_id, name: shop.shop_name }
  editingShopName.value = shop.shop_name
}

async function handleSaveShopName() {
  if (!editingShop.value || !editingShopName.value.trim()) return
  try {
    await $fetch(`/api/shops/${editingShop.value.id}`, {
      method: 'PUT',
      body: { shopName: editingShopName.value },
    })
    // Refresh shops list to show the updated name
    await fetchShops()
    editingShop.value = null
    editingShopName.value = ''
  } catch (err: any) {
    alert(err.message || 'Failed to update shop name')
  }
}

function closeEditShopDialog() {
  editingShop.value = null
  editingShopName.value = ''
}

// Edit account handlers (Account Management tab)
function openEditAccountDialog(account: { account_id: number; account_name: string }) {
  editingAccount.value = { id: account.account_id, name: account.account_name }
  editingAccountName.value = account.account_name
}

async function handleSaveAccountName() {
  if (!editingAccount.value || !editingAccountName.value.trim()) return
  try {
    await $fetch(`/api/accounts/${editingAccount.value.id}`, {
      method: 'PUT',
      body: { accountName: editingAccountName.value },
    })
    await fetchAccounts()
    editingAccount.value = null
    editingAccountName.value = ''
  } catch (err: any) {
    alert(err.message || 'Failed to update account name')
  }
}

function closeEditAccountDialog() {
  editingAccount.value = null
  editingAccountName.value = ''
}

// Track previous linked accounts for detecting changes
const previousLinkedAccountIds = ref<Set<number>>(new Set())

// Link account handlers
function openLinkAccountDialog(shopId: number) {
  linkingShopId.value = shopId
  const linkedAccountIds = getShopAccounts(shopId).map(a => a.account_id)
  previousLinkedAccountIds.value = new Set(linkedAccountIds)
  selectedAccountIds.value = new Set(linkedAccountIds)
}

function toggleAccountSelection(accountId: number) {
  if (selectedAccountIds.value.has(accountId)) {
    selectedAccountIds.value.delete(accountId)
  } else {
    selectedAccountIds.value.add(accountId)
  }
  // Force reactivity update
  selectedAccountIds.value = new Set(selectedAccountIds.value)
}

function closeLinkAccountDialog() {
  linkingShopId.value = null
  selectedAccountIds.value = new Set()
}

async function handleLinkAccounts() {
  if (!linkingShopId.value) return
  try {
    const shopId = linkingShopId.value
    const previousIds = previousLinkedAccountIds.value
    const newIds = selectedAccountIds.value

    // Find accounts to link (in new but not in previous)
    for (const accountId of newIds) {
      if (!previousIds.has(accountId)) {
        await $fetch(`/api/shops/${shopId}/accounts`, {
          method: 'POST',
          body: { accountId: accountId },
        })
      }
    }

    // Find accounts to unlink (in previous but not in new)
    for (const accountId of previousIds) {
      if (!newIds.has(accountId)) {
        await $fetch(`/api/shops/${shopId}/accounts`, {
          method: 'DELETE',
          body: { accountId: accountId },
        })
      }
    }

    // Refresh shop accounts
    await fetchShopAccounts(shopId)
    // Refresh shops list to update account counts
    await fetchShops()
    // Refresh accounts list
    await fetchAccounts()
    closeLinkAccountDialog()
  } catch (err: any) {
    alert(err.message || 'Failed to update account links')
  }
}

async function handleUnlinkAccount(shopId: number, accountId: number) {
  if (!confirm('Unlink this account from the shop?')) return
  try {
    await $fetch(`/api/shops/${shopId}/accounts`, {
      method: 'DELETE',
      body: { accountId: accountId },
    })
    // Refresh shop accounts
    await fetchShopAccounts(shopId)
    // Refresh shops list to update account counts
    await fetchShops()
    // Refresh accounts list
    await fetchAccounts()
  } catch (err: any) {
    alert(err.message || 'Failed to unlink account')
  }
}

// Watch for expanded shops and fetch accounts
import { watch } from 'vue'
watch(expandedShops, async (newExpanded) => {
  for (const shopId of newExpanded) {
    await onShopExpanded(shopId)
  }
}, { deep: true })

// Load data on mount
onMounted(async () => {
  await fetchShops()
  await fetchAccounts()
})
</script>

<template>
  <div class="p-6">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Shops & Accounts</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Manage your shops and accounts</p>
    </div>

    <!-- Main Tabs -->
    <div class="mb-6">
      <div class="inline-flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
        <button
          @click="activeTab = 'shop-management'"
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
          :class="activeTab === 'shop-management' ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-gray-100' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'"
        >
          Shop Management
        </button>
        <button
          @click="activeTab = 'account-management'"
          class="px-4 py-2 rounded-md text-sm font-medium transition-colors"
          :class="activeTab === 'account-management' ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-gray-100' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'"
        >
          Account Management
        </button>
      </div>
    </div>

    <!-- Shop Management Tab -->
    <div v-if="activeTab === 'shop-management'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <!-- Add Shop Form -->
      <div class="p-4 border-b bg-gray-50 dark:bg-gray-800 rounded-t-lg">
        <div class="flex items-center gap-3">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Add Shop</span>
          <div class="flex gap-2 flex-1 max-w-md">
            <input
              v-model="newShopName"
              type="text"
              placeholder="Enter shop name..."
              class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @keyup.enter="handleAddShop"
            />
            <button
              @click="handleAddShop"
              class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <Plus class="w-4 h-4" />
              Add
            </button>
          </div>
        </div>
      </div>

      <!-- Table Header -->
      <div class="grid grid-cols-3 gap-4 px-6 py-3 border-b bg-gray-50 dark:bg-gray-800 text-sm">
        <div class="font-medium text-gray-700 dark:text-gray-300">Shop-Website</div>
        <div class="font-medium text-gray-700 dark:text-gray-300">Accounts</div>
        <div class="font-medium text-gray-700 dark:text-gray-300 text-right">Actions</div>
      </div>

      <!-- Shops List - Expandable Rows -->
      <div v-if="shops.length === 0" class="p-12 text-center">
        <p class="text-gray-500 dark:text-gray-400">No shops found. Add a shop to get started.</p>
      </div>

      <div
        v-for="shop in shops"
        :key="shop.shop_id"
        class="border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <!-- Row Header (Collapsible Trigger) -->
        <div
          class="grid grid-cols-3 gap-4 px-6 py-4 cursor-pointer items-center"
          @click="toggleShop(shop.shop_id)"
        >
          <!-- Shop Name -->
          <div class="flex items-center gap-2">
            <span class="font-medium text-gray-900 dark:text-gray-100">{{ shop.shop_name }}</span>
          </div>

          <!-- Accounts Summary -->
          <div class="text-sm text-gray-600 dark:text-gray-400">
            <span>Accounts: {{ shop.account_count }}</span>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-end gap-2">
            <button class="text-gray-500 dark:text-gray-400 transition-transform" :class="isShopExpanded(shop.shop_id) ? 'rotate-180' : ''" title="Expand/Collapse">
              <ChevronDown class="w-5 h-5" />
            </button>
          </div>
        </div>

        <!-- Expanded Content -->
        <CollapsibleRoot v-if="isShopExpanded(shop.shop_id)" :open="true">
          <CollapsibleContent class="bg-gray-50/50 dark:bg-gray-800/50">
            <div class="grid grid-cols-3 gap-4 px-6 pb-4 pt-2">
              <!-- Shop Details -->
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Shop Details</h3>
                <div class="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <p><span class="font-medium dark:text-gray-300">ID:</span> {{ shop.shop_id }}</p>
                  <p><span class="font-medium dark:text-gray-300">Name:</span> {{ shop.shop_name }}</p>
                  <p><span class="font-medium dark:text-gray-300">Accounts:</span> {{ shop.account_count }}</p>
                  <p><span class="font-medium dark:text-gray-300">Files:</span> {{ shop.file_count }}</p>
                </div>
              </div>

              <!-- Accounts List -->
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Accounts</h3>
                <div v-if="getShopAccounts(shop.shop_id).length === 0" class="text-sm text-gray-500 dark:text-gray-400">
                  No accounts linked. Use "Manage Accounts" to link/unlink
                </div>
                <div v-else class="space-y-2">
                  <div v-for="account in getShopAccounts(shop.shop_id)" :key="account.account_id" class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                    <User class="w-4 h-4 text-gray-400 dark:text-gray-500" />
                    <span>{{ account.account_name }}</span>
                  </div>
                </div>
              </div>

              <!-- Actions Column -->
              <div>
                <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 text-right">Actions</h3>
                <div class="flex flex-col gap-2 items-end">
                  <button
                    @click="openEditShopDialog(shop)"
                    class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors"
                    title="Edit Shop"
                  >
                    <Pencil class="w-4 h-4" />
                    Edit Shop
                  </button>
                  <button
                    @click="openLinkAccountDialog(shop.shop_id)"
                    class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md transition-colors"
                    title="Manage Accounts"
                  >
                    <User class="w-4 h-4" />
                    Manage Accounts
                  </button>
                  <button
                    @click="handleDeleteShop(shop.shop_id)"
                    class="flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md transition-colors"
                    title="Delete Shop"
                  >
                    <Trash2 class="w-4 h-4" />
                    Delete Shop
                  </button>
                </div>
              </div>
            </div>
          </CollapsibleContent>
        </CollapsibleRoot>
      </div>
    </div>

    <!-- Account Management Tab -->
    <div v-else-if="activeTab === 'account-management'" class="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
      <div class="p-6">
        <!-- Add Account Form -->
        <div class="mb-6 flex gap-4">
          <input
            v-model="newAccountName"
            type="text"
            placeholder="Enter account name..."
            class="px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md text-sm text-gray-900 dark:text-gray-100 max-w-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            @keydown.enter="handleCreateAccount"
          />
          <button
            @click="handleCreateAccount"
            class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            <Plus class="w-4 h-4" />
            Add Account
          </button>
        </div>

        <!-- Accounts Table -->
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b bg-gray-50 dark:bg-gray-800">
                <th class="text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Account Name</th>
                <th class="text-left px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Account ID</th>
                <th class="text-right px-4 py-3 text-sm font-medium text-gray-700 dark:text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="account in accounts"
                :key="account.account_id"
                class="border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <td class="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">{{ account.account_name }}</td>
                <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ account.account_id }}</td>
                <td class="px-4 py-3 text-right">
                  <div class="flex gap-2 justify-end">
                    <button
                      @click="openEditAccountDialog(account)"
                      class="p-1.5 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 transition-colors"
                      title="Edit Account Name"
                    >
                      <Pencil class="w-4 h-4" />
                    </button>
                    <button
                      @click="handleDeleteAccountFromManagement(account.account_id)"
                      :disabled="deletingAccount[`management-${account.account_id}`]"
                      class="p-1.5 rounded-md hover:bg-red-100 dark:hover:bg-red-900/20 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete"
                    >
                      <Trash2 class="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Edit Shop Dialog -->
    <Teleport to="body">
      <div v-if="editingShop" class="fixed inset-0 z-50 flex items-center justify-center" @click.self="closeEditShopDialog">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50"></div>
        
        <!-- Dialog -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-6 z-10">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Edit Shop</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">Enter the new name for this shop:</p>
          
          <input
            v-model="editingShopName"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Shop name"
            @keyup.enter="handleSaveShopName"
          />
          
          <div class="flex justify-end gap-3 mt-6">
            <button
              @click="closeEditShopDialog"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              @click="handleSaveShopName"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Edit Account Dialog (Account Management tab) -->
    <Teleport to="body">
      <div v-if="editingAccount" class="fixed inset-0 z-50 flex items-center justify-center" @click.self="closeEditAccountDialog">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50"></div>
        
        <!-- Dialog -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-6 z-10">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Edit Account</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">Enter the new name for this account:</p>
          
          <input
            v-model="editingAccountName"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-md text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Account name"
            @keyup.enter="handleSaveAccountName"
          />
          
          <div class="flex justify-end gap-3 mt-6">
            <button
              @click="closeEditAccountDialog"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              @click="handleSaveAccountName"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Link Account Dialog -->
    <Teleport to="body">
      <div v-if="linkingShopId !== null" class="fixed inset-0 z-50 flex items-center justify-center" @click.self="closeLinkAccountDialog">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50"></div>
        
        <!-- Dialog -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 p-6 z-10 max-h-[80vh] flex flex-col">
          <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Manage Accounts</h2>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">Check accounts to link, uncheck to unlink:</p>
          
          <div class="flex-1 overflow-y-auto space-y-2 mb-4">
            <div v-if="accounts.length === 0" class="text-sm text-gray-500 dark:text-gray-400 italic">No accounts available</div>
            <div
              v-for="account in accounts"
              :key="account.account_id"
              class="flex items-center gap-3 p-3 border rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              :class="selectedAccountIds.has(account.account_id) ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-600'"
            >
              <input
                :id="`account-${account.account_id}`"
                type="checkbox"
                :checked="selectedAccountIds.has(account.account_id)"
                @change="toggleAccountSelection(account.account_id)"
                class="w-4 h-4 text-blue-600 border-gray-300 dark:border-gray-500 rounded focus:ring-blue-500"
              />
              <label :for="`account-${account.account_id}`" class="flex-1 text-sm text-gray-900 dark:text-gray-100 cursor-pointer">
                {{ account.account_name }}
              </label>
            </div>
          </div>
          
          <div class="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              @click="handleLinkAccounts"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
