<script setup lang="ts">
import type { TreeItem, SelectionState } from './FileBrowserTree.vue'
import { computed } from 'vue'
import { ChevronRight, ChevronDown, CheckSquare, CheckCircle2, Square, Circle, Minus, Folder, FolderOpen, ImageIcon, FileText, Loader2 } from 'lucide-vue-next'

const props = defineProps<{
  item: TreeItem
  depth?: number
  searchQuery?: string
  activeFilter?: string
}>()

const nodeDepth = computed(() => props.depth ?? 0)

const emit = defineEmits<{
  expand: [item: TreeItem]
  select: [item: TreeItem]
}>()

// Filter helpers for TreeNode
function matchesFilter(item: TreeItem, filter?: string): boolean {
  const f = filter || 'all'
  if (item.type === 'file') {
    if (f === 'tagged' && !item.isTagged) return false
    if (f === 'untagged' && item.isTagged) return false
    if (f === 'staged' && !item.isStaged) return false
    if (f === 'in-review') return false
  }
  return true
}

function matchesSearch(item: TreeItem, query?: string): boolean {
  const q = (query || '').toLowerCase()
  if (!q) return true
  return item.name.toLowerCase().includes(q) ||
         item.path.toLowerCase().includes(q)
}

function isDirectoryVisible(item: TreeItem, query?: string, filter?: string): boolean {
  if (item.type === 'file') return matchesFilter(item, filter) && matchesSearch(item, query)
  
  const f = filter || 'all'
  if (!item.children) {
    // No children loaded yet - only show if directory name matches search
    return matchesSearch(item, query)
  }
  
  const hasVisibleChildren = item.children.some(child =>
    child.type === 'file' ? matchesFilter(child, filter) && matchesSearch(child, query) : isDirectoryVisible(child, query, filter)
  )
  
  // When filter is not 'all', directory must have visible children
  if (f !== 'all') {
    return hasVisibleChildren
  }
  
  // When filter is 'all', also show if directory name matches search
  return hasVisibleChildren || matchesSearch(item, query)
}

function getVisibleChildren(item: TreeItem, query?: string, filter?: string): TreeItem[] {
  if (!item.children) return []
  return item.children.filter(child =>
    child.type === 'file' ? matchesFilter(child, filter) && matchesSearch(child, query) : isDirectoryVisible(child, query, filter)
  )
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div>
    <!-- Node Row -->
    <div
      :class="['flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors', item.selected ? 'bg-blue-50/50 dark:bg-blue-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800']"
      :style="{ paddingLeft: `${nodeDepth * 16 + 12}px` }"
      @click="emit('select', item)"
    >
      <!-- Expand/Collapse -->
      <button
        v-if="item.type === 'directory'"
        @click.stop="emit('expand', item)"
        class="flex-shrink-0 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
      >
        <ChevronRight v-if="!item.expanded" class="w-3 h-3 text-gray-400" />
        <ChevronDown v-else class="w-3 h-3 text-gray-400" />
      </button>
      <div v-else class="w-4 flex-shrink-0" />

      <!-- Checkbox with selection state indicator -->
            <template v-if="item.type === 'directory'">
              <!-- Full selection: checked box -->
              <CheckSquare v-if="item.selectionState === 'full'" class="w-4 h-4 text-blue-400 flex-shrink-0" />
              <!-- Partial selection: indeterminate (minus sign) -->
              <Minus v-else-if="item.selectionState === 'partial'" class="w-4 h-4 text-blue-400 flex-shrink-0" />
              <!-- No selection: empty circle -->
              <Circle v-else class="w-4 h-4 text-blue-400 flex-shrink-0" />
            </template>
            <component :is="item.selected ? CheckSquare : Circle" v-else class="w-4 h-4 text-blue-400 flex-shrink-0" />

      <!-- Icon -->
      <FolderOpen v-if="item.type === 'directory' && item.expanded" class="w-4 h-4 text-blue-400 flex-shrink-0" />
      <Folder v-else-if="item.type === 'directory'" class="w-4 h-4 text-blue-400 flex-shrink-0" />
      <ImageIcon v-else-if="item.isImage" class="w-4 h-4 text-purple-500 flex-shrink-0" />
      <FileText v-else class="w-4 h-4 text-gray-400 flex-shrink-0" />

      <!-- Name -->
      <span class="text-sm text-gray-600 dark:text-gray-400 truncate">{{ item.name }}</span>

      <!-- Status Pills (files only) -->
      <div v-if="item.type === 'file'" class="flex items-center gap-1 ml-auto flex-shrink-0">
        <!-- Tagged Pill -->
        <span
          v-if="item.isTagged"
          class="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200"
        >
          Tagged
        </span>
        <!-- Untagged Pill -->
        <span
          v-else
          class="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200"
        >
          Untagged
        </span>
        <!-- Staged Pill (future feature) -->
        <span
          v-if="item.isStaged"
          class="px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200"
        >
          Staged
        </span>
      </div>

      <!-- File info -->
      <span v-if="item.type === 'file'" class="text-xs text-gray-400 dark:text-gray-500 ml-2 flex-shrink-0">
        {{ formatFileSize(item.size) }}
      </span>
    </div>

    <!-- Children (recursive) - filtered by search and tag status -->
    <div v-if="item.expanded && getVisibleChildren(item, searchQuery, activeFilter).length > 0" class="tree-children">
      <TreeNode
        v-for="child in getVisibleChildren(item, searchQuery, activeFilter)"
        :key="child.path"
        :item="child"
        :depth="nodeDepth + 1"
        :search-query="searchQuery"
        :active-filter="activeFilter"
        @expand="emit('expand', $event)"
        @select="emit('select', $event)"
      />
    </div>

    <!-- Loading indicator for children -->
    <div v-if="item.expanded && item.hasChildren && !item.children" class="py-1">
      <Loader2 class="w-3 h-3 animate-spin text-blue-500 inline-block" :style="{ marginLeft: `${(nodeDepth + 1) * 16 + 24}px` }" />
    </div>
  </div>
</template>

<style scoped>
.tree-children {
  border-left: 1px solid rgba(128, 128, 128, 0.1);
  margin-left: 16px;
}
</style>
