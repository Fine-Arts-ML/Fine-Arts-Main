<script setup lang="ts">
import { onMounted, computed, watch } from 'vue'
import { useAuth } from '~/composables/useAuth'
import {
  FolderOpen, Folder, FileText, Image as ImageIcon,
  ChevronRight, Home, ChevronDown, ChevronUp,
  List, Grid3X3, RefreshCw, Filter, Save,
  User, HardDrive, ArrowUpFromLine, Trash2, CheckSquare, Square, CheckCircle
} from 'lucide-vue-next'

const { isAdmin, isAuthenticated } = useAuth()

definePageMeta({
  layout: 'default',
  middleware: 'admin',
})

useHead({
  title: 'Browse Folders - Art Management',
})

// File browser types
interface DirectoryItem {
  fileid: number
  name: string
  type: 'directory' | 'file'
  size: number
  mtime: number
  etag?: string
  mimeType?: string
}

interface ListFilesResult {
  path: string
  directories: DirectoryItem[]
  files: DirectoryItem[]
  storageId?: number
}

interface NextcloudUser {
  uid: string
  displayName: string
  storageId: number
  numericId: number
  available: boolean
  role: 'admin' | 'user' | 'guest'
}

// Selected folder for multi-select
interface SelectedFolder {
  userId: string
  path: string
  storageId: number
  displayName: string
}

// State
const fileBrowserPath = ref('')
const fileBrowserLoading = ref(false)
const fileBrowserResult = ref<ListFilesResult | null>(null)
const listViewMode = ref(false)

// User selector state
const allUsers = ref<NextcloudUser[]>([])
const selectedUser = ref<NextcloudUser | null>(null)
const usersLoading = ref(false)
const usersLoaded = ref(false)

// User role filter (multiselect)
const roleFilter = ref<Set<'admin' | 'user' | 'guest'>>(new Set(['admin', 'user', 'guest']))
const roleFilterExpanded = ref(true)

// Selected folders for multi-select
const selectedFolders = ref<SelectedFolder[]>([])
const selectedDirectoryItems = ref<Set<number>>(new Set())

// Saved index config state
const savedIndexConfig = ref<{
  folders: Array<{ path: string; storageId: number; displayName: string }>
} | null>(null)
const isLoadingConfig = ref(false)
const isSaving = ref(false)

// Computed for filtered users by role
const filteredUsers = computed(() => {
  return allUsers.value.filter(u => roleFilter.value.has(u.role))
})

// Computed for current display path
const userHomePath = computed(() => {
  // This would come from useAuth() in a real implementation
  return 'Tom'
})

const currentHomePath = computed(() => {
  if (selectedUser.value) {
    return `/${selectedUser.value.uid}`
  }
  return `/${userHomePath.value}`
})

// Breadcrumbs for directory navigation
const breadcrumbs = computed(() => {
  if (!fileBrowserPath.value) return []
  
  const crumbs: Array<{ path: string; label: string }> = []
  
  if (selectedUser.value) {
    crumbs.push({ path: `/${selectedUser.value.uid}`, label: selectedUser.value.displayName })
  } else {
    crumbs.push({ path: `/${userHomePath.value}`, label: userHomePath.value })
  }
  
  let basePath = crumbs[0].path
  const pathWithoutUser = fileBrowserPath.value.replace(crumbs[0].path, '')
  
  if (pathWithoutUser) {
    const segments = pathWithoutUser.split('/').filter(s => s)
    let currentPath = basePath
    
    for (const segment of segments) {
      currentPath = `${currentPath}/${segment}`
      crumbs.push({ path: currentPath, label: segment })
    }
  }
  
  return crumbs
})

const canGoUp = computed(() => {
  return breadcrumbs.value.length > 1
})

const parentPath = computed(() => {
  if (breadcrumbs.value.length <= 1) return ''
  return breadcrumbs.value[breadcrumbs.value.length - 2].path
})

// Methods
async function loadAllUsers() {
  usersLoading.value = true
  try {
    const result = await $fetch('/api/settings/rag-index/list-users', {
      method: 'GET'
    })
    allUsers.value = result.users || []
    usersLoaded.value = true
    
    const currentUid = userHomePath.value
    const currentUser = allUsers.value.find(u => u.uid === currentUid)
    if (currentUser) {
      selectedUser.value = currentUser
      fileBrowserPath.value = currentHomePath.value
    }
  } catch (error: any) {
    console.error('Failed to load users:', error)
  } finally {
    usersLoading.value = false
  }
}

async function selectUser(user: NextcloudUser) {
  selectedUser.value = user
  fileBrowserPath.value = `/${user.uid}`
  fileBrowserResult.value = null
  selectedDirectoryItems.value.clear()
  await loadSelectedFolders()
  await listFiles()
}

async function loadSelectedFolders() {
  if (!selectedUser.value) return
  try {
    const config = await $fetch('/api/settings/rag-index/index-config', {
      method: 'GET',
    })
    if (config && Array.isArray(config.folders)) {
      selectedFolders.value = config.folders
    } else {
      selectedFolders.value = []
    }
  } catch (error: any) {
    console.error('Failed to load selected folders:', error)
  }
}

function toggleRoleFilter(role: 'admin' | 'user' | 'guest') {
  const newFilter = new Set(roleFilter.value)
  if (newFilter.has(role)) {
    newFilter.delete(role)
  } else {
    newFilter.add(role)
  }
  roleFilter.value = newFilter
}

function isRoleSelected(role: 'admin' | 'user' | 'guest'): boolean {
  return roleFilter.value.has(role)
}

function toggleAllRoles() {
  if (roleFilter.value.size === 3) {
    roleFilter.value = new Set()
  } else {
    roleFilter.value = new Set(['admin', 'user', 'guest'])
  }
}

async function loadIndexConfig() {
  isLoadingConfig.value = true
  try {
    const config = await $fetch('/api/settings/rag-index/index-config', {
      method: 'GET',
    })
    savedIndexConfig.value = config
    
    if (Array.isArray(config.folders) && config.folders.length > 0) {
      if (allUsers.value.length > 0) {
        const firstFolder = config.folders[0]
        const username = firstFolder.path.split('/')[1]
        const configUser = allUsers.value.find(u => u.uid === username)
        if (configUser) {
          selectedUser.value = configUser
          fileBrowserPath.value = firstFolder.path
          await loadSelectedFolders()
          await listFiles()
        } else {
          selectedUser.value = allUsers.value[0]
          await loadSelectedFolders()
          await listFiles()
        }
      }
    }
  } catch (error: any) {
    console.error('Failed to load index config:', error)
  } finally {
    isLoadingConfig.value = false
  }
}

async function saveIndexConfig() {
  isSaving.value = true
  try {
    await $fetch('/api/settings/rag-index/index-config', {
      method: 'POST',
      body: {
        folders: selectedFolders.value.map(f => ({
          path: f.path,
          storageId: f.storageId,
          displayName: f.displayName,
        })),
      },
    })
    await loadSelectedFolders()
  } catch (error: any) {
    console.error('Failed to save index config:', error)
  } finally {
    isSaving.value = false
  }
}

function navigateToBreadcrumb(index: number) {
  const targetPath = breadcrumbs.value[index].path
  fileBrowserPath.value = targetPath
  selectedDirectoryItems.value.clear()
  listFiles()
}

async function goUp() {
  if (!canGoUp.value) return
  fileBrowserPath.value = parentPath.value
  selectedDirectoryItems.value.clear()
  await listFiles()
}

async function listFiles() {
  if (!fileBrowserPath.value.trim()) return
  
  const userId = selectedUser.value?.uid || userHomePath.value
  const storageNumericId = selectedUser.value?.storageId.toString()
  
  fileBrowserLoading.value = true
  fileBrowserResult.value = null
  try {
    const result = await $fetch('/api/settings/rag-index/list-files', {
      method: 'GET',
      params: {
        path: fileBrowserPath.value,
        userId: userId,
        storageNumericId: storageNumericId
      }
    })
    fileBrowserResult.value = result
  } catch (error: any) {
    console.error('Failed to list files:', error)
    alert(`Failed to list files: ${error.message || 'Unknown error'}`)
  } finally {
    fileBrowserLoading.value = false
  }
}

function navigateToDirectory(item: DirectoryItem) {
  if (item.type === 'directory') {
    const currentPath = fileBrowserPath.value.endsWith('/') 
      ? fileBrowserPath.value 
      : `${fileBrowserPath.value}/`
    fileBrowserPath.value = `${currentPath}${item.name}`
    listFiles()
  }
}

function toggleDirectorySelection(item: DirectoryItem) {
  const newSelection = new Set(selectedDirectoryItems.value)
  if (newSelection.has(item.fileid)) {
    newSelection.delete(item.fileid)
  } else {
    newSelection.add(item.fileid)
  }
  selectedDirectoryItems.value = newSelection
}

function selectAllDirectories() {
  if (!fileBrowserResult.value) return
  const allDirIds = new Set(fileBrowserResult.value.directories.map(d => d.fileid))
  if (selectedDirectoryItems.value.size === allDirIds.size) {
    selectedDirectoryItems.value.clear()
  } else {
    selectedDirectoryItems.value = allDirIds
  }
}

function addSelectedFoldersToIndex() {
  if (!fileBrowserResult.value || selectedDirectoryItems.value.size === 0) return
  
  const userId = selectedUser.value?.uid || userHomePath.value
  const storageId = selectedUser.value?.storageId || 0
  
  for (const item of fileBrowserResult.value.directories) {
    if (selectedDirectoryItems.value.has(item.fileid)) {
      const folderPath = `${fileBrowserPath.value}/${item.name}`
      const exists = selectedFolders.value.some(f => f.path === folderPath)
      if (!exists) {
        selectedFolders.value.push({
          userId,
          path: folderPath,
          storageId,
          displayName: `${selectedUser.value?.displayName || userId}/${item.name}`
        })
      }
    }
  }
  
  selectedDirectoryItems.value.clear()
  saveSelectedFolders()
}

function removeSelectedFolder(index: number) {
  selectedFolders.value.splice(index, 1)
  saveSelectedFolders()
}

function isDirectorySelected(fileid: number): boolean {
  if (selectedDirectoryItems.value.has(fileid)) return true
  
  if (fileBrowserResult.value) {
    const dir = fileBrowserResult.value.directories.find(d => d.fileid === fileid)
    if (dir) {
      const dirPath = `${fileBrowserPath.value}/${dir.name}`
      return selectedFolders.value.some(f => f.path === dirPath)
    }
  }
  
  return false
}

async function saveSelectedFolders() {
  if (!selectedUser.value) return
  
  try {
    await $fetch('/api/settings/rag-index/index-config', {
      method: 'POST',
      body: {
        folders: selectedFolders.value.map(f => ({
          path: f.path,
          storageId: f.storageId,
          displayName: f.displayName,
        })),
      },
    })
  } catch (error: any) {
    console.error('Failed to save selected folders:', error)
  }
}

function formatFileSizeFromBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleDateString()
}

onMounted(async () => {
  await loadAllUsers()
  await loadIndexConfig()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-3 mb-2">
        <FolderOpen class="w-6 h-6 text-gray-600 dark:text-gray-400" />
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Browse Folders</h2>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Select the folders to index for the Tags & Tagging pipeline. Selected folders will be used when scanning for files to tag.
      </p>
    </div>

    <!-- Browse Interface -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div class="flex h-[600px] gap-0">
        <!-- Sidebar - User List with Role Filter -->
        <div class="w-80 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <!-- Sidebar Header -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <HardDrive class="w-4 h-4" />
                File Browser
              </h3>
              <button
                v-if="!usersLoaded"
                @click="loadAllUsers"
                class="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 rounded hover:bg-blue-200 dark:hover:bg-blue-800"
              >
                Load Users
              </button>
            </div>

            <!-- Role Filter -->
            <div class="mb-3">
              <button
                @click="roleFilterExpanded = !roleFilterExpanded"
                class="flex items-center gap-2 text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 hover:text-gray-800 dark:hover:text-gray-200"
              >
                <Filter class="w-3 h-3" />
                Filter by Role
                <ChevronDown v-if="roleFilterExpanded" class="w-3 h-3" />
                <ChevronRight v-else class="w-3 h-3" />
              </button>
              
              <div v-if="roleFilterExpanded" class="space-y-1 ml-5">
                <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-800 dark:hover:text-gray-200">
                  <input
                    type="checkbox"
                    :checked="isRoleSelected('admin')"
                    @change="toggleRoleFilter('admin')"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  Admin
                </label>
                <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-800 dark:hover:text-gray-200">
                  <input
                    type="checkbox"
                    :checked="isRoleSelected('user')"
                    @change="toggleRoleFilter('user')"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  User
                </label>
                <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 cursor-pointer hover:text-gray-800 dark:hover:text-gray-200">
                  <input
                    type="checkbox"
                    :checked="isRoleSelected('guest')"
                    @change="toggleRoleFilter('guest')"
                    class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  Guest
                </label>
                <button
                  @click="toggleAllRoles"
                  class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                >
                  {{ roleFilter.size === 3 ? 'Clear All' : 'Select All' }}
                </button>
              </div>
            </div>
          </div>
          
          <!-- User List -->
          <div class="flex-1 overflow-y-auto">
            <div v-if="usersLoading" class="p-4 text-center">
              <RefreshCw class="w-6 h-6 animate-spin text-blue-500 mx-auto" />
            </div>
            
            <div v-else>
              <div
                v-for="u in filteredUsers"
                :key="u.uid"
                class="border-b border-gray-100 dark:border-gray-700 last:border-0"
              >
                <button
                  @click="selectUser(u)"
                  :class="[
                    'w-full px-4 py-2 flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors',
                    selectedUser?.uid === u.uid ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
                  ]"
                >
                  <User class="w-4 h-4 text-gray-500" />
                  <div class="text-left">
                    <div class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ u.displayName }}</div>
                    <div class="flex items-center gap-2">
                      <span class="text-xs text-gray-500 dark:text-gray-400">@{{ u.uid }}</span>
                      <span class="text-xs px-1.5 py-0.5 rounded-full"
                        :class="{
                          'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300': u.role === 'guest',
                          'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300': u.role === 'user',
                          'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300': u.role === 'admin'
                        }"
                      >
                        {{ u.role }}
                      </span>
                    </div>
                  </div>
                </button>
              </div>
              
              <div v-if="filteredUsers.length === 0" class="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                No users match the selected roles
              </div>
            </div>
          </div>
          
          <!-- Selected Folders Panel -->
          <div class="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex flex-col">
            <div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2 flex items-center justify-between">
              <span>Selected Folders ({{ selectedFolders.length }})</span>
              <button
                @click="selectedFolders = []; saveSelectedFolders()"
                class="text-xs text-red-500 hover:text-red-700"
              >
                Clear All
              </button>
            </div>
            
            <div class="flex-1 min-h-0 overflow-y-auto space-y-1">
              <div
                v-for="(folder, index) in selectedFolders"
                :key="index"
                class="flex items-center justify-between text-xs bg-white dark:bg-gray-700 rounded px-2 py-1.5 border border-gray-200 dark:border-gray-600"
              >
                <span class="truncate flex-1 text-gray-700 dark:text-gray-300">{{ folder.displayName }}</span>
                <button
                  @click="removeSelectedFolder(index)"
                  class="ml-2 text-red-500 hover:text-red-700 flex-shrink-0"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Main Content Area - Directory Browser -->
        <div class="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
          <!-- Header with Breadcrumbs and Controls -->
          <div class="p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center gap-2">
              <Home class="w-4 h-4 text-gray-500 flex-shrink-0" />
              
              <!-- Breadcrumb Navigation -->
              <div class="flex items-center gap-1 flex-1 overflow-x-auto">
                <button
                  v-for="(crumb, index) in breadcrumbs"
                  :key="index"
                  @click="navigateToBreadcrumb(index)"
                  class="flex items-center gap-1 text-sm whitespace-nowrap"
                >
                  <span
                    :class="index === breadcrumbs.length - 1 
                      ? 'font-medium text-gray-900 dark:text-gray-100' 
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'"
                  >
                    {{ crumb.label }}
                  </span>
                  <ChevronRight v-if="index < breadcrumbs.length - 1" class="w-3 h-3 text-gray-400 flex-shrink-0" />
                </button>
              </div>
              
              <!-- Go Up Button -->
              <button
                v-if="canGoUp"
                @click="goUp"
                class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-1 flex-shrink-0"
              >
                <ArrowUpFromLine class="w-3 h-3" />
                Up
              </button>
              
              <!-- View Toggle -->
              <button
                @click="listViewMode = !listViewMode"
                class="p-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded flex-shrink-0"
                :title="listViewMode ? 'Grid View' : 'List View'"
              >
                <component :is="listViewMode ? Grid3X3 : List" class="w-4 h-4" />
              </button>
            </div>
          </div>
          
          <!-- Results Area -->
          <div class="flex-1 overflow-y-auto p-4">
            <!-- Loading State -->
            <div v-if="fileBrowserLoading" class="flex items-center justify-center h-full">
              <div class="text-center">
                <RefreshCw class="w-12 h-12 animate-spin text-blue-500 mx-auto mb-3" />
                <p class="text-sm text-gray-500 dark:text-gray-400">Loading files...</p>
              </div>
            </div>
            
            <!-- Results Display -->
            <div v-else-if="fileBrowserResult">
              <!-- Directories -->
              <div v-if="fileBrowserResult.directories.length > 0" class="mb-6">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <Folder class="w-4 h-4 text-blue-500" />
                    Folders ({{ fileBrowserResult.directories.length }})
                  </h4>
                  <button
                    @click="selectAllDirectories"
                    class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center gap-1"
                  >
                    <component :is="selectedDirectoryItems.size === fileBrowserResult.directories.length ? CheckSquare : Square" class="w-3 h-3" />
                    {{ selectedDirectoryItems.size === fileBrowserResult.directories.length ? 'Deselect All' : 'Select All' }}
                  </button>
                </div>
                
                <!-- Grid View (Default) -->
                <div v-if="!listViewMode" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  <div
                    v-for="dir in fileBrowserResult.directories"
                    :key="dir.fileid"
                  >
                    <button
                      @click="navigateToDirectory(dir)"
                      :class="[
                        'relative flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-lg border hover:border-blue-500 dark:hover:border-blue-500 hover:shadow-md transition-all cursor-pointer group w-full',
                        isDirectorySelected(dir.fileid) ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-200 dark:border-gray-700'
                      ]"
                    >
                      <div
                        @click.stop="toggleDirectorySelection(dir)"
                        class="absolute top-2 left-2 cursor-pointer z-10"
                      >
                        <component :is="isDirectorySelected(dir.fileid) ? CheckSquare : Square" class="w-5 h-5 text-gray-400 hover:text-blue-500" />
                      </div>
                      <Folder class="w-10 h-10 text-blue-500 group-hover:text-blue-600 transition-colors mt-4" />
                      <span class="text-sm text-gray-700 dark:text-gray-300 text-center truncate w-full">{{ dir.name }}</span>
                    </button>
                  </div>
                </div>
                
                <!-- List View -->
                <div v-else class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <div class="grid grid-cols-12 gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-700 text-xs font-medium text-gray-500 dark:text-gray-400">
                    <div class="col-span-1"></div>
                    <div class="col-span-6">Name</div>
                    <div class="col-span-3">Size</div>
                    <div class="col-span-2">Modified</div>
                  </div>
                  <div
                    v-for="dir in fileBrowserResult.directories"
                    :key="dir.fileid"
                    @click="navigateToDirectory(dir)"
                    :class="[
                      'grid grid-cols-12 gap-2 px-4 py-3 items-center cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors',
                      isDirectorySelected(dir.fileid) ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                    ]"
                  >
                    <div class="col-span-1" @click.stop="toggleDirectorySelection(dir)">
                      <component :is="isDirectorySelected(dir.fileid) ? CheckSquare : Square" class="w-5 h-5 text-gray-400 hover:text-blue-500 cursor-pointer" />
                    </div>
                    <div class="col-span-6 flex items-center gap-2">
                      <Folder class="w-4 h-4 text-blue-500 flex-shrink-0" />
                      <span class="text-sm text-gray-700 dark:text-gray-300 truncate">{{ dir.name }}</span>
                    </div>
                    <div class="col-span-3 text-sm text-gray-500 dark:text-gray-400">-</div>
                    <div class="col-span-2 text-xs text-gray-500 dark:text-gray-400">{{ formatDate(dir.mtime / 1000) }}</div>
                  </div>
                </div>
              </div>
              
              <!-- Files -->
              <div v-if="fileBrowserResult.files.length > 0">
                <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 flex items-center gap-2">
                  <FileText class="w-4 h-4 text-gray-500" />
                  Files ({{ fileBrowserResult.files.length }})
                </h4>
                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  <div
                    v-for="file in fileBrowserResult.files"
                    :key="file.fileid"
                    class="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 transition-all"
                  >
                    <ImageIcon v-if="file.name.match(/\.(jpg|jpeg|png|gif|webp|svg)$/)" class="w-10 h-10 text-purple-500" />
                    <FileText v-else class="w-10 h-10 text-gray-400" />
                    <div class="text-center">
                      <p class="text-sm text-gray-700 dark:text-gray-300 truncate w-full">{{ file.name }}</p>
                      <p class="text-xs text-gray-500 dark:text-gray-400">{{ formatFileSizeFromBytes(file.size) }}</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Empty State -->
              <div v-if="fileBrowserResult.directories.length === 0 && fileBrowserResult.files.length === 0" class="flex flex-col items-center justify-center h-64 text-center">
                <FolderOpen class="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
                <p class="text-sm text-gray-500 dark:text-gray-400">No files or folders found at this path</p>
                <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">{{ fileBrowserPath }}</p>
              </div>
            </div>
            
            <!-- Initial State -->
            <div v-else class="flex flex-col items-center justify-center h-full text-center">
              <FolderOpen class="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
              <p class="text-sm text-gray-500 dark:text-gray-400 mb-2">Select a user from the sidebar to browse their files</p>
              <p class="text-xs text-gray-400 dark:text-gray-500">Or navigate using the breadcrumbs above</p>
            </div>
          </div>
          
          <!-- Bottom Action Bar -->
          <div v-if="fileBrowserResult && !fileBrowserLoading" class="p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <div v-if="selectedDirectoryItems.size > 0" class="flex items-center gap-2">
                <span class="text-sm text-gray-600 dark:text-gray-400">
                  {{ selectedDirectoryItems.size }} folder(s) selected
                </span>
                <button
                  @click="addSelectedFoldersToIndex"
                  class="px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 flex items-center gap-1"
                >
                  <CheckCircle class="w-4 h-4" />
                  Add to Index
                </button>
              </div>
              <div v-else class="text-sm text-gray-500 dark:text-gray-400">
                Select folders to add them to the index
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Save Button -->
    <div class="flex justify-end">
      <button
        @click="saveIndexConfig"
        :disabled="isSaving"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      >
        <Save class="w-4 h-4" />
        {{ isSaving ? 'Saving...' : 'Save Folder Selection' }}
      </button>
    </div>
  </div>
</template>
