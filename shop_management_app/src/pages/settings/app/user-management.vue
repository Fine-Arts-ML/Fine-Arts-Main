<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuth } from '~/composables/useAuth'
import { Users, RefreshCw, Search, UserCheck, UserX, Shield, User, EyeOff, AlertCircle } from 'lucide-vue-next'

const { isAdmin, isAuthenticated } = useAuth()

definePageMeta({
  layout: 'default',
  middleware: 'admin',
})

useHead({
  title: 'User Management - Art Management',
})

// State
interface User {
  id: number
  nextcloudUid: string
  displayName: string
  email: string
  role: 'guest' | 'user' | 'admin'
  allowedGalleryIds: number[]
  isActive: boolean
  nextcloudGroups: string[]
  createdAt: string
  updatedAt: string
}

const users = ref<User[]>([])
const loading = ref(false)
const syncing = ref(false)
const searchQuery = ref('')
const roleFilter = ref('all')
const activeFilter = ref('all')
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)

// Sync stats
const syncStats = ref({
  synced: 0,
  created: 0,
  updated: 0,
  errors: [] as string[],
})

// Computed
const filteredUsers = computed(() => {
  return users.value
})

const syncProgress = computed(() => {
  if (!syncing.value) return 0
  const total = syncStats.value.synced + syncStats.value.errors.length
  if (total === 0) return 0
  return Math.round(((syncStats.value.synced + syncStats.value.updated) / Math.max(total, 1)) * 100)
})

// Watch for filter changes and reload users
watch([searchQuery, roleFilter, activeFilter], () => {
  loadUsers()
})

// Methods
async function loadUsers() {
  loading.value = true
  error.value = null
  
  try {
    const params = new URLSearchParams()
    if (searchQuery.value) params.set('search', searchQuery.value)
    if (roleFilter.value !== 'all') params.set('role', roleFilter.value)
    if (activeFilter.value !== 'all') params.set('active', activeFilter.value)
    
    const queryString = params.toString()
    const result = await $fetch(`/api/users${queryString ? '?' + queryString : ''}`)
    users.value = result.users || []
  } catch (e: any) {
    error.value = e?.statusMessage || 'Failed to load users'
    console.error('[user-management] Load users error:', e)
  } finally {
    loading.value = false
  }
}

async function syncUsers() {
  syncing.value = true
  error.value = null
  syncStats.value = { synced: 0, created: 0, updated: 0, errors: [] }
  
  try {
    const result = await $fetch('/api/users/sync', { method: 'POST' })
    syncStats.value = result
    
    showSuccess(`Sync complete: ${result.created} created, ${result.updated} updated, ${result.errors.length} errors`)
    await loadUsers()
  } catch (e: any) {
    error.value = e?.statusMessage || 'Sync failed'
    console.error('[user-management] Sync error:', e)
  } finally {
    syncing.value = false
  }
}

async function updateRole(user: User, newRole: string) {
  if (user.role === newRole) return
  
  try {
    await $fetch(`/api/users/${user.id}/role`, {
      method: 'PUT',
      body: { role: newRole },
    })
    
    user.role = newRole as 'guest' | 'user' | 'admin'
    showSuccess(`User ${user.nextcloudUid} role updated to ${newRole}`)
    await loadUsers()
  } catch (e: any) {
    error.value = e?.statusMessage || 'Failed to update role'
    console.error('[user-management] Update role error:', e)
  }
}

async function toggleActive(user: User) {
  try {
    await $fetch(`/api/users/${user.id}/active`, {
      method: 'PUT',
      body: { isActive: !user.isActive },
    })
    
    user.isActive = !user.isActive
    showSuccess(`User ${user.nextcloudUid} ${user.isActive ? 'activated' : 'deactivated'}`)
    await loadUsers()
  } catch (e: any) {
    error.value = e?.statusMessage || 'Failed to update user status'
    console.error('[user-management] Toggle active error:', e)
  }
}

function showSuccess(message: string) {
  successMessage.value = message
  setTimeout(() => {
    successMessage.value = null
  }, 3000)
}

function getRoleBadgeClass(role: string): string {
  const classes = {
    guest: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    user: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  }
  return classes[role as keyof typeof classes] || 'bg-gray-100 text-gray-800'
}

function getRoleIcon(role: string) {
  if (role === 'admin') return Shield
  if (role === 'guest') return EyeOff
  return User
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div class="flex items-center gap-3">
          <Users class="w-6 h-6 text-gray-600 dark:text-gray-400" />
          <div>
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">User Management</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Manage users, roles, and permissions. Users are synced from Nextcloud groups.
            </p>
          </div>
        </div>
        
        <Button
          variant="outline"
          @click="syncUsers"
          :disabled="syncing || loading"
          class="gap-2"
        >
          <RefreshCw :class="['w-4 h-4', syncing && 'animate-spin']" />
          {{ syncing ? 'Syncing...' : 'Sync Now' }}
        </Button>
      </div>
    </div>

    <!-- Sync Stats -->
    <div v-if="syncStats.created > 0 || syncStats.updated > 0 || syncStats.errors.length > 0" 
         class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div class="flex items-center gap-4 text-sm">
        <span class="text-green-600 dark:text-green-400">
          <UserCheck class="w-4 h-4 inline mr-1" />
          {{ syncStats.synced }} synced
        </span>
        <span v-if="syncStats.created > 0" class="text-blue-600 dark:text-blue-400">
          +{{ syncStats.created }} new
        </span>
        <span v-if="syncStats.updated > 0" class="text-yellow-600 dark:text-yellow-400">
          ~{{ syncStats.updated }} updated
        </span>
        <span v-if="syncStats.errors.length > 0" class="text-red-600 dark:text-red-400">
          {{ syncStats.errors.length }} errors
        </span>
      </div>
      <div v-if="syncStats.errors.length > 0" class="mt-2 text-xs text-red-600 dark:text-red-400">
        <div v-for="err in syncStats.errors" :key="err" class="truncate">{{ err }}</div>
      </div>
    </div>

    <!-- Success Message -->
    <div v-if="successMessage" 
         class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4 text-green-700 dark:text-green-400 text-sm">
      {{ successMessage }}
    </div>

    <!-- Error Message -->
    <div v-if="error" 
         class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-red-700 dark:text-red-400 text-sm flex items-center gap-2">
      <AlertCircle class="w-4 h-4 flex-shrink-0" />
      {{ error }}
    </div>

    <!-- Filters -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
      <div class="flex flex-col sm:flex-row gap-4">
        <!-- Search -->
        <div class="flex-1 relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search users by username, name, or email..."
            class="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        
        <!-- Role Filter -->
        <select
          v-model="roleFilter"
          class="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="all">All Roles</option>
          <option value="guest">Guest</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
        
        <!-- Active Filter -->
        <select
          v-model="activeFilter"
          class="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="all">All Users</option>
          <option value="true">Active Only</option>
          <option value="false">Inactive Only</option>
        </select>
      </div>
    </div>

    <!-- User Table -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead class="bg-gray-50 dark:bg-gray-900/50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Email</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Role</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Nextcloud Groups</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
              <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
            <tr v-if="loading">
              <td colspan="6" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                <RefreshCw class="w-6 h-6 inline mr-2 animate-spin" />
                Loading users...
              </td>
            </tr>
            
            <tr v-else-if="filteredUsers.length === 0">
              <td colspan="6" class="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                <Users class="w-12 h-12 mx-auto mb-3 opacity-50" />
                No users found
              </td>
            </tr>
            
            <tr v-for="user in filteredUsers" :key="user.id" 
                :class="!user.isActive && 'opacity-50'">
              <!-- User -->
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                    <span class="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {{ user.nextcloudUid.charAt(0).toUpperCase() }}
                    </span>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {{ user.displayName || user.nextcloudUid }}
                    </div>
                    <div class="text-sm text-gray-500 dark:text-gray-400">
                      @{{ user.nextcloudUid }}
                    </div>
                  </div>
                </div>
              </td>
              
              <!-- Email -->
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900 dark:text-gray-100">
                  {{ user.email || '-' }}
                </div>
              </td>
              
              <!-- Role -->
              <td class="px-6 py-4 whitespace-nowrap">
                <select
                  :value="user.role"
                  @change="updateRole(user, ($event.target as HTMLSelectElement).value)"
                  :disabled="user.nextcloudUid === 'Tom'"
                  class="px-2.5 py-1.5 text-xs font-medium border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="guest">Guest</option>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              
              <!-- Nextcloud Groups -->
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="group in user.nextcloudGroups"
                    :key="group"
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300"
                  >
                    {{ group }}
                  </span>
                  <span v-if="user.nextcloudGroups.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
                    No groups
                  </span>
                </div>
              </td>
              
              <!-- Status -->
              <td class="px-6 py-4 whitespace-nowrap">
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium"
                      :class="user.isActive 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'">
                  <UserCheck v-if="user.isActive" class="w-3 h-3" />
                  <UserX v-else class="w-3 h-3" />
                  {{ user.isActive ? 'Active' : 'Inactive' }}
                </span>
              </td>
              
              <!-- Actions -->
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm">
                <button
                  @click="toggleActive(user)"
                  class="inline-flex items-center px-3 py-1.5 rounded text-xs font-medium transition-colors"
                  :class="user.isActive
                    ? 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20'
                    : 'text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20'"
                >
                  {{ user.isActive ? 'Deactivate' : 'Activate' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Footer -->
      <div v-if="filteredUsers.length > 0" class="bg-gray-50 dark:bg-gray-900/50 px-6 py-3 border-t border-gray-200 dark:border-gray-700">
        <p class="text-sm text-gray-500 dark:text-gray-400">
          Showing {{ filteredUsers.length }} of {{ users.length }} users
        </p>
      </div>
    </div>

    <!-- Info Card -->
    <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
      <h3 class="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2">How role assignment works</h3>
      <ul class="text-sm text-blue-700 dark:text-blue-400 space-y-1">
        <li>• Users in Nextcloud <strong>Guest</strong> group → assigned <strong>Guest</strong> role</li>
        <li>• Users in Nextcloud <strong>admin</strong> group → assigned <strong>Admin</strong> role</li>
        <li>• Users not in any group → assigned <strong>User</strong> role (default)</li>
        <li>• Roles sync automatically on login from Nextcloud groups</li>
        <li>• Admins can manually override roles in this interface</li>
      </ul>
    </div>
  </div>
</template>
