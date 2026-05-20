<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  Folder, FolderOpen, FileText, Image as ImageIcon,
  ChevronRight, ChevronDown, CheckSquare, CheckCircle2,
  Loader2, Filter, Search,
} from 'lucide-vue-next'
import TreeNode from './TreeNode.vue'

export interface AccessibleFolder {
  path: string
  storageId: number
  displayName: string
}

export type SelectionState = 'full' | 'partial' | 'none'

export interface TreeItem {
  fileid: number | string
  name: string
  path: string
  type: 'directory' | 'file'
  size: number
  mtime: number
  mimeType?: string
  isImage: boolean
  children?: TreeItem[]
  expanded: boolean
  selected: boolean
  selectionState?: SelectionState
  hasChildren: boolean
  storageId?: number
  userId?: string
  isTagged?: boolean
  isStaged?: boolean
}

const props = defineProps<{
  accessibleFolders: AccessibleFolder[]
  scanApiPath?: string
  hideTagDescribeButton?: boolean
  hideStagedFilter?: boolean
}>()

const emit = defineEmits<{
  'update:selectedFolders': [folders: Set<string>]
  'update:selectedFiles': [files: Set<string>]
  'update:selectedFileIds': [ids: Set<number>]
  'scan': [paths: string[]]
  'filter-change': [filter: FileFilter]
  'proceed': []
}>()

export type FileFilter = 'all' | 'tagged' | 'untagged' | 'staged' | 'in-review'
const activeFilter = ref<FileFilter>('all')
const searchQuery = ref('')

const rootFolders = ref<TreeItem[]>([])
const loadingFolders = ref(false)
const scanning = ref(false)

// Load accessible folders on mount
onMounted(async () => {
  console.log('[FileBrowserTree] onMounted - component mounted, loading folders...')
  await loadAccessibleFolders()
})

async function loadAccessibleFolders() {
  console.log('[FileBrowserTree] loadAccessibleFolders - START: loading folders from API')
  loadingFolders.value = true
  try {
    const result = await $fetch('/api/tags-and-tagging/accessible-folders', { method: 'GET' })
    if (result.success && result.folders) {
      console.log('[FileBrowserTree] loadAccessibleFolders - received', result.folders.length, 'folders from API')
      rootFolders.value = result.folders.map((folder: AccessibleFolder) => {
        const userId = folder.path.split('/')[0] || 'Tom'
        return {
          fileid: Date.now() + Math.random(),
          name: folder.displayName.split('/').pop() || folder.displayName,
          path: folder.path,
          type: 'directory' as const,
          size: 0,
          mtime: 0,
          isImage: false,
          expanded: false,
          selected: false,
          hasChildren: true,
          storageId: folder.storageId,
          userId: userId,
        }
      })
      console.log('[FileBrowserTree] loadAccessibleFolders - rootFolders created with', rootFolders.value.length, 'items, all selected=false')
      await preloadChildren(rootFolders.value)
      console.log('[FileBrowserTree] loadAccessibleFolders - preloadChildren complete')
      
      // After loading, try to restore persisted selection
      const persistedPaths = restoreSelectedFoldersFromStorage()
      if (persistedPaths && persistedPaths.length > 0) {
        applyPersistedSelection(persistedPaths)
      } else {
        console.log('[FileBrowserTree] loadAccessibleFolders - no persisted selection to restore')
      }
    }
  } catch (error: any) {
    console.error('[FileBrowserTree] loadAccessibleFolders - FAILED:', error)
  } finally {
    loadingFolders.value = false
    console.log('[FileBrowserTree] loadAccessibleFolders - DONE (loadingFolders=false)')
  }
}

async function preloadChildren(folders: TreeItem[]) {
  for (const folder of folders) {
    if (folder.hasChildren && !folder.children) {
      await loadDirectoryChildren(folder, true) // Recursively load all descendants
    }
  }
}

async function loadDirectoryChildren(item: TreeItem, recursive = false) {
  try {
    const userId = item.userId || item.path.split('/')[0] || 'Tom'
    const storageNumericId = item.storageId?.toString()

    const result = await $fetch('/api/settings/rag-index/list-files', {
      method: 'GET',
      params: {
        path: item.path,
        userId: userId,
        storageNumericId: storageNumericId,
      },
    })

    if (result) {
      const directories = (result.directories || []).map((dir: any) => ({
        fileid: dir.fileid,
        name: dir.name,
        path: `${item.path}/${dir.name}`,
        type: 'directory' as const,
        size: 0,
        mtime: dir.mtime,
        isImage: false,
        expanded: false,
        selected: false,
        hasChildren: true,
        storageId: item.storageId,
        userId: userId,
      }))

      const files = (result.files || []).map((file: any) => ({
        fileid: file.fileid,
        name: file.name,
        path: `${item.path}/${file.name}`,
        type: 'file' as const,
        size: file.size,
        mtime: file.mtime,
        mimeType: file.mime_type,
        isImage: file.mime_type?.startsWith('image/'),
        isTagged: (file.tagCount || 0) > 0,
        isStaged: false, // Reserved for future feature
        expanded: false,
        selected: false,
        hasChildren: false,
      }))

      item.children = [...directories, ...files]

      // Recursively load children for all subdirectories if requested
      if (recursive) {
        for (const dir of directories) {
          const dirItem = item.children?.find(c => c.path === dir.path)
          if (dirItem) {
            await loadDirectoryChildren(dirItem, true)
          }
        }
      }
    }
  } catch (error: any) {
    console.error(`Failed to load children for ${item.path}:`, error)
  }
}

async function toggleExpand(item: TreeItem) {
  item.expanded = !item.expanded
  if (item.expanded && item.hasChildren && !item.children) {
    await loadDirectoryChildren(item, true) // Recursively load all descendants
  }
}

function toggleItemSelection(item: TreeItem) {
  const newSelected = !item.selected
  console.log('[FileBrowserTree] toggleItemSelection -', item.path, '→', newSelected)
  item.selected = newSelected
  
  // FIX: Update selectionState to match the new selected state
  if (item.type === 'directory') {
    if (!item.selected) {
      item.selectionState = 'none'
    } else {
      item.selectionState = 'full'
    }
  }
  
  if (item.type === 'directory' && item.children) {
    setChildrenSelection(item.children, item.selected)
  }
  
  // FIX: Update parent selection states up the tree
  updateParentSelectionStates()
  
  const selectedPaths = getSelectedPaths()
  const selectedFilePaths = getSelectedFilePaths()
  // Persist selection directly on user interaction (not via watch)
  persistSelectedFolders(selectedPaths)
  const selectedFileIds = getSelectedFileIds()
  console.log('[FileBrowserTree] toggleItemSelection - emitted selectedFolders:', Array.from(selectedPaths), 'selectedFiles:', Array.from(selectedFilePaths), 'selectedFileIds:', Array.from(selectedFileIds))
  emit('update:selectedFolders', selectedPaths)
  emit('update:selectedFiles', selectedFilePaths)
  emit('update:selectedFileIds', selectedFileIds)
}

function setChildrenSelection(children: TreeItem[], selected: boolean) {
  for (const child of children) {
    if (child.type === 'file') {
      // For files: only select if they match both filter and search
      if (!matchesFilter(child) || !matchesSearch(child)) {
        continue
      }
    }
    
    // Always set selected state for directories (even if not visible due to filter)
    // so they can be toggled on/off regardless of current filter state
    child.selected = selected
    
    // Only recurse into children that are visible under current filter
    if (child.type === 'directory' && child.children) {
      setChildrenSelection(child.children, selected)
    }
  }
}

function getSelectedPaths(): Set<string> {
  const paths = new Set<string>()
  
  function collectPaths(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected) {
        paths.add(item.path)
      }
      if (item.children && item.type === 'directory') {
        collectPaths(item.children)
      }
    }
  }
  
  collectPaths(rootFolders.value)
  return paths
}

// Get only selected FILE paths (not directories)
function getSelectedFilePaths(): Set<string> {
  const paths = new Set<string>()
  
  function collectFilePaths(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected && item.type === 'file') {
        paths.add(item.path)
      }
      if (item.children && item.type === 'directory') {
        collectFilePaths(item.children)
      }
    }
  }
  
  collectFilePaths(rootFolders.value)
  return paths
}

// Get only selected FILE numeric IDs (from oc_filecache.fileid)
function getSelectedFileIds(): Set<number> {
  const ids = new Set<number>()
  
  function collectFileIds(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected && item.type === 'file' && typeof item.fileid === 'number') {
        ids.add(item.fileid)
      }
      if (item.children && item.type === 'directory') {
        collectFileIds(item.children)
      }
    }
  }
  
  collectFileIds(rootFolders.value)
  return ids
}

// Persist selected folder paths to localStorage
function persistSelectedFolders(paths: Set<string>) {
  try {
    localStorage.setItem('tagPipeline.selectedFolderPaths', JSON.stringify(Array.from(paths)))
    console.log('[FileBrowserTree] persistSelectedFolders - saved:', Array.from(paths))
  } catch (e) {
    console.error('[FileBrowserTree] persistSelectedFolders - failed:', e)
  }
}

// Restore selected folder paths from localStorage
function restoreSelectedFoldersFromStorage(): string[] | null {
  try {
    const persisted = localStorage.getItem('tagPipeline.selectedFolderPaths')
    if (persisted) {
      const paths: string[] = JSON.parse(persisted)
      console.log('[FileBrowserTree] restoreSelectedFoldersFromStorage - found persisted paths:', paths)
      return paths
    }
  } catch (e) {
    console.log('[FileBrowserTree] restoreSelectedFoldersFromStorage - no persisted selection found')
  }
  return null
}

// Recursively find a tree item by its full path, returns the matched item or null
function findItemByPath(item: TreeItem, targetPath: string): TreeItem | null {
  if (item.path === targetPath) {
    return item
  }
  if (item.children) {
    for (const child of item.children) {
      const found = findItemByPath(child, targetPath)
      if (found) {
        return found
      }
    }
  }
  return null
}

// Recursively select all descendants of an item
function selectItemAndDescendants(item: TreeItem) {
  item.selected = true
  item.selectionState = 'full'
  if (item.children) {
    setChildrenSelection(item.children, true)
  }
}

// Recursively expand all parent folders that contain a matching path
function expandParentsOfItem(targetPath: string, items: TreeItem[]): boolean {
  for (const item of items) {
    if (item.path === targetPath) {
      return true // This item matches, parent should expand
    }
    
    if (item.children) {
      // Check if any descendant matches
      const childMatches = expandParentsOfItem(targetPath, item.children)
      
      if (childMatches) {
        // Expand this parent to show the selected child
        item.expanded = true
        return true
      }
    }
  }
  return false
}

// Expand all parent folders that contain selected items
function expandParentsOfSelected(): void {
  const selectedFilePaths = getSelectedFilePaths()
  for (const filePath of selectedFilePaths) {
    expandParentsOfItem(filePath, rootFolders.value)
  }
}

// Recursively update parent selection states by traversing the entire tree
function updateParentSelectionStates() {
  function getVisibleChildrenForState(item: TreeItem): TreeItem[] {
    if (!item.children) return []
    return item.children.filter(child => {
      if (child.type === 'file') {
        return matchesFilter(child) && matchesSearch(child)
      }
      return isDirectoryVisible(child)
    })
  }

  function updateItemSelectionState(item: TreeItem): void {
    if (!item.children || item.children.length === 0) return
    
    // Only count visible children for selection state when filter/search is active
    const visibleChildren = getVisibleChildrenForState(item)
    const totalChildren = visibleChildren.length
    const selectedChildren = visibleChildren.filter(c => c.selected).length
    
    if (selectedChildren === 0) {
      item.selectionState = 'none'
      item.selected = false
    } else if (selectedChildren === totalChildren) {
      item.selectionState = 'full'
      item.selected = true
    } else {
      item.selectionState = 'partial'
      item.selected = false
    }
    
    // Recursively update children
    for (const child of item.children) {
      if (child.children && child.type === 'directory') {
        updateItemSelectionState(child)
      }
    }
  }
  
  // Start from all root folders
  for (const root of rootFolders.value) {
    updateItemSelectionState(root)
  }
}

// Apply persisted selection to the loaded tree items by recursively searching for matching paths
function applyPersistedSelection(persistedPaths: string[]) {
  console.log('[FileBrowserTree] applyPersistedSelection - restoring', persistedPaths.length, 'selections')
  let restoredCount = 0
  
  for (const targetPath of persistedPaths) {
    // Search the entire tree for a matching path
    for (const rootFolder of rootFolders.value) {
      const matchedItem = findItemByPath(rootFolder, targetPath)
      if (matchedItem) {
        // Select the matched item and all its descendants
        selectItemAndDescendants(matchedItem)
        restoredCount++
        console.log('[FileBrowserTree] applyPersistedSelection - restored selection for:', targetPath)
        break
      }
    }
  }
  
  // Update parent folder selection states
  updateParentSelectionStates()
  
  // Expand all parent folders that contain selected items so user can see them
  expandParentsOfSelected()
  
  console.log('[FileBrowserTree] applyPersistedSelection - restored', restoredCount, 'of', persistedPaths.length, 'paths')
  const restoredPaths = getSelectedPaths()
  const restoredFilePaths = getSelectedFilePaths()
  const restoredFileIds = getSelectedFileIds()
  console.log('[FileBrowserTree] applyPersistedSelection - emitted restored selectedFolders:', Array.from(restoredPaths), 'selectedFiles:', Array.from(restoredFilePaths), 'selectedFileIds:', Array.from(restoredFileIds))
  emit('update:selectedFolders', restoredPaths)
  emit('update:selectedFiles', restoredFilePaths)
  emit('update:selectedFileIds', restoredFileIds)
}


function selectAll() {
  const allSelected = rootFolders.value.every(f => f.selected)
  const newState = !allSelected
  console.log('[FileBrowserTree] selectAll - toggling to:', newState, '(was allSelected:', allSelected, ')')
  for (const folder of rootFolders.value) {
    folder.selected = newState
    if (folder.children) {
      setChildrenSelection(folder.children, newState)
    }
  }
  const selectedPaths = getSelectedPaths()
  const selectedFilePaths = getSelectedFilePaths()
  const selectedFileIds = getSelectedFileIds()
  console.log('[FileBrowserTree] selectAll - emitted selectedFolders:', Array.from(selectedPaths), 'selectedFiles:', Array.from(selectedFilePaths), 'selectedFileIds:', Array.from(selectedFileIds))
  emit('update:selectedFolders', selectedPaths)
  emit('update:selectedFiles', selectedFilePaths)
  emit('update:selectedFileIds', selectedFileIds)
}

function isAllSelected(): boolean {
  return rootFolders.value.length > 0 && rootFolders.value.every(f => f.selected)
}

function handleScan() {
  const selectedPaths = Array.from(getSelectedPaths())
  emit('scan', selectedPaths)
}

function handleProceed() {
  emit('proceed')
}

function handleFilterChange(filter: FileFilter) {
  activeFilter.value = filter
  emit('filter-change', filter)
}

const filteredCount = computed(() => {
  let count = 0
  let taggedCount = 0
  let untaggedCount = 0
  
  function countItems(items: TreeItem[]) {
    for (const item of items) {
      if (item.type === 'file') {
        count++
        if (item.isTagged) taggedCount++
        else untaggedCount++
      }
      if (item.children && item.type === 'directory') {
        countItems(item.children)
      }
    }
  }
  
  countItems(rootFolders.value)
  return { total: count, tagged: taggedCount, untagged: untaggedCount }
})

const selectedCount = computed(() => {
  let count = 0
  
  function countSelected(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected && item.type === 'file') count++
      if (item.children && item.type === 'directory') {
        countSelected(item.children)
      }
    }
  }
  
  countSelected(rootFolders.value)
  return count
})

// Check if a file item matches the current filter criteria
function matchesFilter(item: TreeItem): boolean {
  const filter = activeFilter.value
  if (item.type === 'file') {
    if (filter === 'tagged' && !item.isTagged) return false
    if (filter === 'untagged' && item.isTagged) return false
    if (filter === 'staged' && !item.isStaged) return false
    if (filter === 'in-review') return false
  }
  return true
}

// Check if an item matches the search query
function matchesSearch(item: TreeItem): boolean {
  const query = searchQuery.value.toLowerCase()
  if (!query) return true
  return item.name.toLowerCase().includes(query) ||
         item.path.toLowerCase().includes(query)
}

// Check if a directory should be visible (matches search or has visible children)
// When filter is not 'all', directories must contain files matching the filter to be visible
function isDirectoryVisible(item: TreeItem): boolean {
  if (item.type === 'file') return matchesFilter(item) && matchesSearch(item)
  
  // For directories: visible only if it has children that match the filter
  if (!item.children) {
    // No children loaded yet - only show if directory name matches search
    // (filter can't be applied without loading children)
    return matchesSearch(item)
  }
  
  const hasVisibleChildren = item.children.some(child =>
    child.type === 'file' ? matchesFilter(child) && matchesSearch(child) : isDirectoryVisible(child)
  )
  
  // If filter is not 'all', directory must have visible children
  if (activeFilter.value !== 'all') {
    return hasVisibleChildren
  }
  
  // If filter is 'all', also show if directory name matches search
  return hasVisibleChildren || matchesSearch(item)
}

// Computed filtered list that preserves reactive object references
// This uses a flat filter (no deep clone) so expand/collapse state works correctly
const filteredFolders = computed(() => {
  // Return root items that match the filter
  // Children are shown/hidden by TreeNode component based on expanded state
  return rootFolders.value.filter(item => isDirectoryVisible(item))
})

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(timestamp: number): string {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleDateString()
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Toolbar -->
    <div class="flex items-center gap-2 flex-wrap pb-3">
      <!-- Search -->
      <div class="relative flex-1 min-w-[200px]">
        <Search class="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search folders..."
          class="w-full pl-9 pr-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <!-- Filters -->
      <div class="flex items-center gap-1 flex-wrap">
        <Filter class="w-4 h-4 text-gray-400 flex-shrink-0" />
        <button
          @click="handleFilterChange('all')"
          :class="['px-2 py-1 text-xs rounded transition-colors flex items-center gap-1', activeFilter === 'all' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600']"
        >
          All
          <span class="px-1.5 py-0.5 rounded-full text-[10px]">{{ filteredCount.total }}</span>
        </button>
        <button
          @click="handleFilterChange('tagged')"
          :class="['px-2 py-1 text-xs rounded transition-colors flex items-center gap-1', activeFilter === 'tagged' ? 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600']"
        >
          Tagged
          <span class="px-1.5 py-0.5 rounded-full bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200 text-[10px]">{{ filteredCount.tagged }}</span>
        </button>
        <button
          @click="handleFilterChange('untagged')"
          :class="['px-2 py-1 text-xs rounded transition-colors flex items-center gap-1', activeFilter === 'untagged' ? 'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600']"
        >
          Untagged
          <span class="px-1.5 py-0.5 rounded-full bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200 text-[10px]">{{ filteredCount.untagged }}</span>
        </button>
        <button
          v-if="!hideStagedFilter"
          @click="handleFilterChange('staged')"
          :class="['px-2 py-1 text-xs rounded transition-colors flex items-center gap-1 opacity-60', activeFilter === 'staged' ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600']"
          title="Coming soon"
        >
          Staged
          <span class="px-1.5 py-0.5 rounded-full bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200 text-[10px]">0</span>
        </button>
        <button
          @click="handleFilterChange('in-review')"
          :class="['px-2 py-1 text-xs rounded transition-colors flex items-center gap-1 opacity-60', activeFilter === 'in-review' ? 'bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600']"
          title="Coming soon"
        >
          In Review
          <span class="px-1.5 py-0.5 rounded-full bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200 text-[10px]">0</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loadingFolders" class="flex items-center justify-center py-8">
      <div class="text-center">
        <Loader2 class="w-8 h-8 animate-spin text-blue-500 mx-auto mb-2" />
        <p class="text-sm text-gray-500 dark:text-gray-400">Loading folders...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="rootFolders.length === 0" class="flex flex-col items-center justify-center py-8 text-center">
      <Folder class="w-12 h-12 text-gray-300 dark:text-gray-600 mb-3" />
      <p class="text-sm text-gray-500 dark:text-gray-400">No folders available yet.</p>
      <p class="text-xs text-gray-400 dark:text-gray-500 mt-1">Contact your administrator to configure accessible folders.</p>
    </div>

    <!-- Tree View -->
    <div v-else class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden flex-1 flex flex-col min-h-0">
      <!-- Select All Header -->
      <div class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        <button
          @click="selectAll"
          class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
        >
          <component :is="isAllSelected() ? CheckSquare : CheckCircle2" class="w-4 h-4" />
          {{ isAllSelected() ? 'Deselect All' : 'Select All' }}
        </button>
        <span class="text-xs text-gray-500 dark:text-gray-400">
          {{ selectedCount }} selected
        </span>
      </div>

      <!-- Folder Tree - Scrollable area -->
      <div class="flex-1 overflow-y-auto bg-white dark:bg-gray-900 min-h-0 p-2">
        <template v-for="folder in filteredFolders" :key="folder.path">
          <TreeNode
            :item="folder"
            :depth="0"
            :search-query="searchQuery"
            :active-filter="activeFilter"
            @expand="toggleExpand($event)"
            @select="toggleItemSelection($event)"
          />
        </template>
      </div>
    </div>

    <!-- Proceed Button (Tag & Describe) - hidden when hideTagDescribeButton prop is true -->
    <button
      v-if="!hideTagDescribeButton"
      @click="handleProceed"
      :disabled="selectedCount === 0"
      class="w-full px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors flex-shrink-0 mt-3"
    >
      Tag & Describe {{ selectedCount }} Files
      <ChevronRight class="w-4 h-4" />
    </button>
  </div>
</template>
