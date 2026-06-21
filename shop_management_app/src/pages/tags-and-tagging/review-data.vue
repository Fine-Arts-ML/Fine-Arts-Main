<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAuth } from '~/composables/useAuth'
import { useTagPipeline } from '~/composables/useTagPipeline'
import {
  Tag,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Plus,
  Trash2,
  Save,
  ArrowLeft,
  Upload,
  Pencil,
  X,
  Check,
  Square,
  SquareCheck,
  ChevronUp,
  ChevronDown,
} from 'lucide-vue-next'

const { isAdmin } = useAuth()
const { selectedFiles } = useTagPipeline()

definePageMeta({
  middleware: 'tags-pipeline',
})

useHead({
  title: 'Review Data - Tags & Tagging',
})

// ========== Types ==========
interface StagedTag {
  id: number
  name: string
}

interface StagedDescription {
  id: number
  description: string
  createdAt: string
}

interface FileStagedData {
  fileId: string
  fileName: string
  filePath: string
  tags: StagedTag[]
  descriptions: StagedDescription[]
}

interface ApiResponse {
  success: boolean
  tagsByFile: Record<string, StagedTag[]>
  descriptionsByFile: Record<string, StagedDescription[]>
  fileMetadata: Record<string, { fileName: string; filePath: string }>
  summary: {
    totalFilesWithTags: number
    totalFilesWithDescriptions: number
    totalStagedTags: number
    totalStagedDescriptions: number
  }
}

// ========== State ==========
const loading = ref(true)
const pushing = ref(false)
const pushLoading = ref<'tags' | 'descriptions' | 'both' | null>(null)
const message = ref<{ type: 'success' | 'error'; text: string } | null>(null)
const activeTab = ref<'tags' | 'descriptions'>('tags')
const selectedFilesSet = ref<Set<string>>(new Set())
const fileDataMap = ref<Map<string, FileStagedData>>(new Map())
const summary = ref({
  totalFilesWithTags: 0,
  totalFilesWithDescriptions: 0,
  totalStagedTags: 0,
  totalStagedDescriptions: 0,
})

// For adding new tags
const newTagInput = ref('')
const addingTagTo = ref<string | null>(null)

// For editing descriptions
const editingDescId = ref<number | null>(null)
const editingDescText = ref('')

// Expansion state for file rows (tags/descriptions collapsible)
const expandedFiles = ref<Set<string>>(new Set())

// ========== Delete by File State ==========
const showDeleteConfirm = ref(false)
const deleteTargetFileIds = ref<string[]>([])
const deleteType = ref<'tags' | 'descriptions' | 'both'>('both')
const deleting = ref(false)

// Toggle file row expansion
function toggleFileExpansion(fileId: string): void {
  if (expandedFiles.value.has(fileId)) {
    expandedFiles.value.delete(fileId)
  } else {
    expandedFiles.value.add(fileId)
  }
}

// Check if a file row is expanded
function isFileExpanded(fileId: string): boolean {
  return expandedFiles.value.has(fileId)
}

// ========== Computed ==========
const fileList = computed(() => Array.from(fileDataMap.value.values()))

const hasData = computed(() => fileList.value.length > 0)

const selectedCount = computed(() => selectedFilesSet.value.size)

const hasSelectedFiles = computed(() => selectedFilesSet.value.size > 0)

const allSelected = computed(() => {
  if (fileList.value.length === 0) return false
  return fileList.value.every(f => selectedFilesSet.value.has(f.fileId))
})

const tagsOnlyFiles = computed(() => fileList.value.filter(f => f.tags.length > 0))
const descOnlyFiles = computed(() => fileList.value.filter(f => f.descriptions.length > 0))

// ========== Methods ==========
async function fetchStagedData() {
  loading.value = true
  message.value = null
  try {
    const result = await $fetch<ApiResponse>('/api/settings/rag-index/staging/fetch', {
      method: 'GET',
    })

    if (result.success) {
      const map = new Map<string, FileStagedData>()
      const fileMetadata = result.fileMetadata || {}

      // Build file list from tags
      for (const [fileId, tags] of Object.entries(result.tagsByFile)) {
        if (!map.has(fileId)) {
          const meta = fileMetadata[fileId] || { fileName: fileId, filePath: fileId }
          map.set(fileId, { fileId, fileName: meta.fileName, filePath: meta.filePath, tags: [], descriptions: [] })
        }
        map.get(fileId)!.tags = tags
      }

      // Build file list from descriptions
      for (const [fileId, descriptions] of Object.entries(result.descriptionsByFile)) {
        if (!map.has(fileId)) {
          const meta = fileMetadata[fileId] || { fileName: fileId, filePath: fileId }
          map.set(fileId, { fileId, fileName: meta.fileName, filePath: meta.filePath, tags: [], descriptions: [] })
        }
        map.get(fileId)!.descriptions = descriptions
      }

      fileDataMap.value = map
      summary.value = result.summary
    }
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to fetch staged data' }
  } finally {
    loading.value = false
  }
}

function toggleFileSelection(fileId: string) {
  const set = selectedFilesSet.value
  if (set.has(fileId)) {
    set.delete(fileId)
    selectedFilesSet.value = new Set(set)
  } else {
    const newSet = new Set(set)
    newSet.add(fileId)
    selectedFilesSet.value = newSet
  }
}

function selectAll() {
  const newSet = new Set<string>()
  for (const file of fileList.value) {
    newSet.add(file.fileId)
  }
  selectedFilesSet.value = newSet
}

function deselectAll() {
  selectedFilesSet.value = new Set()
}

async function pushToProduction(type: 'tags' | 'descriptions' | 'both') {
  pushLoading.value = type
  pushing.value = true
  message.value = null

  try {
    const body: Record<string, any> = { type }

    if (hasSelectedFiles.value) {
      body.file_ids = Array.from(selectedFilesSet.value)
    }

    const result = await $fetch('/api/settings/rag-index/staging/push-to-db', {
      method: 'POST',
      body,
    })

    if (result.success) {
      message.value = {
        type: 'success',
        text: `Successfully pushed ${type}: ${result.tagsPushed || 0} tags, ${result.descriptionsPushed || 0} descriptions`,
      }
      // Refresh data
      await fetchStagedData()
    } else {
      message.value = { type: 'error', text: result.error || 'Failed to push data' }
    }
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to push data' }
  } finally {
    pushLoading.value = null
    pushing.value = false
  }
}

async function addTagToFile(fileId: string) {
  const tagName = newTagInput.value.trim()
  if (!tagName) return

  try {
    await $fetch('/api/settings/rag-index/staging/update', {
      method: 'PUT',
      body: {
        operation: 'add_tag',
        targetId: 0,
        fileId,
        data: { tagName },
      },
    })
    newTagInput.value = ''
    addingTagTo.value = null
    await fetchStagedData()
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to add tag' }
  }
}

async function removeTag(fileId: string, tagId: number) {
  try {
    await $fetch('/api/settings/rag-index/staging/update', {
      method: 'PUT',
      body: {
        operation: 'remove_tag',
        targetId: tagId,
        fileId,
        data: {},
      },
    })
    await fetchStagedData()
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to remove tag' }
  }
}

function startEditingDesc(desc: StagedDescription) {
  editingDescId.value = desc.id
  editingDescText.value = desc.description
}

function cancelEditingDesc() {
  editingDescId.value = null
  editingDescText.value = ''
}

async function saveEditingDesc(fileId: string, descId: number) {
  try {
    await $fetch('/api/settings/rag-index/staging/update', {
      method: 'PUT',
      body: {
        operation: 'update_description',
        targetId: descId,
        fileId,
        data: { description: editingDescText.value },
      },
    })
    editingDescId.value = null
    editingDescText.value = ''
    await fetchStagedData()
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to save description' }
  }
}

async function deleteDescription(fileId: string, descId: number) {
  try {
    await $fetch('/api/settings/rag-index/staging/delete', {
      method: 'DELETE',
      query: { type: 'description', id: String(descId) },
    })
    await fetchStagedData()
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to delete description' }
  }
}

// ========== Delete by File Functions ==========
function openDeleteConfirm(fileId: string): void {
  deleteTargetFileIds.value = [fileId]
  deleteType.value = 'both'
  showDeleteConfirm.value = true
}

function openBulkDeleteConfirm(): void {
  deleteTargetFileIds.value = Array.from(selectedFilesSet.value)
  deleteType.value = 'both'
  showDeleteConfirm.value = true
}

async function confirmDelete(): Promise<void> {
  if (deleteTargetFileIds.value.length === 0) return
  
  deleting.value = true
  showDeleteConfirm.value = false
  
  try {
    const result = await $fetch('/api/settings/rag-index/staging/delete-by-file', {
      method: 'POST',
      body: {
        file_ids: deleteTargetFileIds.value,
        type: deleteType.value
      }
    })

    if (result.success) {
      message.value = {
        type: 'success',
        text: `Deleted ${deleteType.value} for ${deleteTargetFileIds.value.length} file(s)`
      }
      // Clear selections and refresh
      selectedFilesSet.value = new Set()
      await fetchStagedData()
    } else {
      message.value = { type: 'error', text: result.error || 'Failed to delete staging data' }
    }
  } catch (error: any) {
    message.value = { type: 'error', text: error.message || 'Failed to delete staging data' }
  } finally {
    deleting.value = false
    deleteTargetFileIds.value = []
  }
}

function cancelDelete(): void {
  showDeleteConfirm.value = false
  deleteTargetFileIds.value = []
}

function formatFileName(filePath: string): string {
  const parts = filePath.split('/')
  return parts[parts.length - 1] || filePath
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// Check if file is likely an image (by extension)
function isImageFile(fileName: string): boolean {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico']
  const lowerName = fileName.toLowerCase()
  return imageExtensions.some(ext => lowerName.endsWith(ext))
}

// ========== Lifecycle ==========
onMounted(() => {
  fetchStagedData()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Review Data</h1>
      </div>
      <div class="flex items-center gap-2">
      </div>
    </div>

    <!-- Message Banner -->
    <div
      v-if="message"
      class="p-4 rounded-lg flex items-center gap-3"
      :class="message.type === 'success' ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800' : 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800'"
    >
      <component :is="message.type === 'success' ? CheckCircle : XCircle" class="w-5 h-5 flex-shrink-0" />
      <span>{{ message.text }}</span>
      <button @click="message = null" class="ml-auto p-1 hover:opacity-70">
        <X class="w-4 h-4" />
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="flex flex-col items-center gap-4">
        <Loader2 class="w-12 h-12 animate-spin text-blue-600" />
        <p class="text-gray-600 dark:text-gray-400">Loading staged data...</p>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasData" class="flex flex-col items-center justify-center py-20">
      <Tag class="w-16 h-16 text-gray-400 mb-4" />
      <h3 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">No Staged Data</h3>
      <p class="text-gray-600 dark:text-gray-400 mb-6 text-center max-w-md">
        There are no staged tags or descriptions to review. Generate tags or descriptions on the "Tags & Descriptions" page first.
      </p>
      <NuxtLink
        to="/tags-and-tagging/tags"
        class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Go to Tags & Descriptions
      </NuxtLink>
    </div>

    <!-- Main Content -->
    <div v-else class="space-y-4">
      <!-- Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-600 dark:text-gray-400">Files with Tags</p>
          <p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ summary.totalFilesWithTags }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-600 dark:text-gray-400">Files with Descriptions</p>
          <p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ summary.totalFilesWithDescriptions }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-600 dark:text-gray-400">Total Staged Tags</p>
          <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{{ summary.totalStagedTags }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
          <p class="text-sm text-gray-600 dark:text-gray-400">Total Staged Descriptions</p>
          <p class="text-2xl font-bold text-purple-600 dark:text-purple-400">{{ summary.totalStagedDescriptions }}</p>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="flex gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg w-fit">
        <button
          @click="activeTab = 'tags'"
          class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors"
          :class="activeTab === 'tags' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'"
        >
          <Tag class="w-4 h-4" />
          Tags ({{ summary.totalStagedTags }})
        </button>
        <button
          @click="activeTab = 'descriptions'"
          class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors"
          :class="activeTab === 'descriptions' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'"
        >
          <FileText class="w-4 h-4" />
          Descriptions ({{ summary.totalStagedDescriptions }})
        </button>
      </div>

      <!-- Tab Content: Tags (with inline file selection) -->
      <div v-if="activeTab === 'tags'" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <!-- Section Header -->
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-blue-500">●</span>
            <h3 class="font-medium text-gray-900 dark:text-gray-100">Staged Tags ({{ summary.totalStagedTags }})</h3>
          </div>
          <!-- Selection Controls -->
          <div class="flex items-center gap-2">
            <button
              @click.stop="selectAll"
              class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Select All
            </button>
            <button
              @click.stop="deselectAll"
              class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Deselect All
            </button>
          </div>
        </div>
        
        <!-- File List Items -->
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <div
            v-for="file in fileList"
            :key="file.fileId"
            class="p-4 space-y-3"
            :class="selectedFilesSet.has(file.fileId) ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''"
          >
            <!-- File Header Row (always visible) -->
            <div class="flex items-center gap-3">
              <!-- Expand/Collapse Chevron -->
              <button
                @click.stop="toggleFileExpansion(file.fileId)"
                class="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <ChevronUp v-if="isFileExpanded(file.fileId)" class="w-4 h-4" />
                <ChevronDown v-else class="w-4 h-4" />
              </button>
              
              <!-- Delete File Button -->
              <button
                @click.stop="openDeleteConfirm(file.fileId)"
                class="flex-shrink-0 text-red-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                title="Delete all staging data for this file"
              >
                <Trash2 class="w-4 h-4" />
              </button>
              
              <!-- Selection Checkbox -->
              <button
                @click.stop="toggleFileSelection(file.fileId)"
                class="flex-shrink-0"
              >
                <component :is="selectedFilesSet.has(file.fileId) ? SquareCheck : Square" class="w-5 h-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
              </button>
              
              <!-- Thumbnail Preview (for image files) -->
              <div v-if="isImageFile(file.fileName)" class="flex-shrink-0">
                <img
                  :src="`/api/files/preview-proxy/${file.fileId}?x=64&y=64`"
                  :alt="file.fileName"
                  class="w-12 h-12 rounded object-cover border border-gray-200 dark:border-gray-700"
                  loading="lazy"
                />
              </div>
              
              <!-- File Info -->
              <div class="flex-1 min-w-0">
                <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ file.fileName }}</h4>
                <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ file.filePath }}</p>
              </div>
              
              <!-- Count Badges -->
              <div class="flex items-center gap-2 flex-shrink-0">
                <span v-if="file.tags.length" class="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                  {{ file.tags.length }} tag(s)
                </span>
                <span v-if="file.descriptions.length" class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
                  {{ file.descriptions.length }} desc(s)
                </span>
              </div>
            </div>
            
            <!-- Collapsible Review Data (only visible when expanded) -->
            <div v-if="isFileExpanded(file.fileId)" class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
              <!-- Tags Display -->
              <div>
                <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Staged Tags:</label>
                <div v-if="file.tags.length" class="flex flex-wrap gap-2">
                  <span
                    v-for="tag in file.tags"
                    :key="tag.id"
                    class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                  >
                    {{ tag.name }}
                    <button
                      @click.stop="removeTag(file.fileId, tag.id)"
                      class="p-0.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    >
                      <X class="w-3 h-3" />
                    </button>
                  </span>
                </div>
                <div v-else class="text-sm text-gray-500 dark:text-gray-400 italic">
                  No tags for this file
                </div>
              </div>
              
              <!-- Add Tag Input -->
              <div class="flex gap-2">
                <button
                  v-if="!addingTagTo || addingTagTo !== file.fileId"
                  @click.stop="addingTagTo = file.fileId; newTagInput = ''"
                  class="flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:underline"
                >
                  <Plus class="w-3 h-3" />
                  Add Tag
                </button>
                <template v-else>
                  <input
                    v-model="newTagInput"
                    :key="file.fileId"
                    type="text"
                    placeholder="Enter tag name"
                    class="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    @keyup.enter="addTagToFile(file.fileId)"
                    @keydown.escape="addingTagTo = null"
                  />
                  <button
                    @click.stop="addTagToFile(file.fileId)"
                    :disabled="!newTagInput.trim()"
                    class="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Check class="w-3 h-3" />
                    Add
                  </button>
                  <button
                    @click.stop="addingTagTo = null"
                    class="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <X class="w-3 h-3" />
                    Cancel
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tab Content: Descriptions (with inline file selection) -->
      <div v-else-if="activeTab === 'descriptions'" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <!-- Section Header -->
        <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-purple-500">●</span>
            <h3 class="font-medium text-gray-900 dark:text-gray-100">Staged Descriptions ({{ summary.totalStagedDescriptions }})</h3>
          </div>
          <!-- Selection Controls -->
          <div class="flex items-center gap-2">
            <button
              @click.stop="selectAll"
              class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Select All
            </button>
            <button
              @click.stop="deselectAll"
              class="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600"
            >
              Deselect All
            </button>
          </div>
        </div>
        
        <!-- File List Items -->
        <div class="divide-y divide-gray-200 dark:divide-gray-700">
          <div
            v-for="file in fileList"
            :key="file.fileId"
            class="p-4 space-y-3"
            :class="selectedFilesSet.has(file.fileId) ? 'bg-blue-50/50 dark:bg-blue-900/10' : ''"
          >
            <!-- File Header Row (always visible) -->
            <div class="flex items-center gap-3">
              <!-- Expand/Collapse Chevron -->
              <button
                @click.stop="toggleFileExpansion(file.fileId)"
                class="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <ChevronUp v-if="isFileExpanded(file.fileId)" class="w-4 h-4" />
                <ChevronDown v-else class="w-4 h-4" />
              </button>
              
              <!-- Delete File Button -->
              <button
                @click.stop="openDeleteConfirm(file.fileId)"
                class="flex-shrink-0 text-red-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                title="Delete all staging data for this file"
              >
                <Trash2 class="w-4 h-4" />
              </button>
              
              <!-- Selection Checkbox -->
              <button
                @click.stop="toggleFileSelection(file.fileId)"
                class="flex-shrink-0"
              >
                <component :is="selectedFilesSet.has(file.fileId) ? SquareCheck : Square" class="w-5 h-5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
              </button>
              
              <!-- Thumbnail Preview (for image files) -->
              <div v-if="isImageFile(file.fileName)" class="flex-shrink-0">
                <img
                  :src="`/api/files/preview-proxy/${file.fileId}?x=64&y=64`"
                  :alt="file.fileName"
                  class="w-12 h-12 rounded object-cover border border-gray-200 dark:border-gray-700"
                  loading="lazy"
                />
              </div>
              
              <!-- File Info -->
              <div class="flex-1 min-w-0">
                <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ file.fileName }}</h4>
                <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ file.filePath }}</p>
              </div>
              
              <!-- Count Badges -->
              <div class="flex items-center gap-2 flex-shrink-0">
                <span v-if="file.tags.length" class="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                  {{ file.tags.length }} tag(s)
                </span>
                <span v-if="file.descriptions.length" class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
                  {{ file.descriptions.length }} desc(s)
                </span>
              </div>
            </div>
            
            <!-- Collapsible Review Data (only visible when expanded) -->
            <div v-if="isFileExpanded(file.fileId)" class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
              <!-- Descriptions Display -->
              <div>
                <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Staged Descriptions:</label>
                <div v-if="file.descriptions.length === 0" class="text-sm text-gray-500 dark:text-gray-400 italic">
                  No descriptions for this file
                </div>
                <div v-else class="space-y-3">
                  <div
                    v-for="desc in file.descriptions"
                    :key="desc.id"
                    class="group"
                  >
                    <!-- Display Mode -->
                    <div v-if="editingDescId !== desc.id" class="flex items-start gap-3">
                      <div class="flex-1 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                        <p class="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap">{{ desc.description }}</p>
                      </div>
                      <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                        <button
                          @click.stop="startEditingDesc(desc)"
                          class="p-1.5 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                          title="Edit"
                        >
                          <Pencil class="w-4 h-4 text-gray-600 dark:text-gray-400" />
                        </button>
                        <button
                          @click.stop="deleteDescription(file.fileId, desc.id)"
                          class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
                          title="Delete"
                        >
                          <Trash2 class="w-4 h-4 text-red-600 dark:text-red-400" />
                        </button>
                      </div>
                    </div>

                    <!-- Edit Mode -->
                    <div v-else class="flex flex-col gap-2">
                      <textarea
                        v-model="editingDescText"
                        rows="4"
                        class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-vertical"
                      />
                      <div class="flex gap-2">
                        <button
                          @click.stop="saveEditingDesc(file.fileId, desc.id)"
                          :disabled="!editingDescText.trim()"
                          class="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <Save class="w-3 h-3" />
                          Save
                        </button>
                        <button
                          @click.stop="cancelEditingDesc"
                          class="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!-- End of collapsible review data -->
          </div>
        </div>
      </div>

      <!-- Bulk Actions Bar -->
      <div
        v-if="hasData"
        class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4"
      >
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="flex items-center gap-3">
            <span class="text-sm text-gray-600 dark:text-gray-400">
              <template v-if="hasSelectedFiles">{{ selectedCount }} file(s) selected — only selected will be pushed</template>
              <template v-else>Click files above to select, or push all</template>
            </span>
            <!-- Bulk Delete Button -->
            <button
              v-if="hasSelectedFiles"
              @click="openBulkDeleteConfirm"
              :disabled="deleting"
              class="flex items-center gap-2 px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Trash2 class="w-4 h-4" />
              Delete Selected
            </button>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <button
              @click="pushToProduction('tags')"
              :disabled="pushing"
              class="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <component :is="pushLoading === 'tags' ? Loader2 : Tag" class="w-4 h-4" :class="{ 'animate-spin': pushLoading === 'tags' }" />
              Push Tags Only
            </button>
            <button
              @click="pushToProduction('descriptions')"
              :disabled="pushing"
              class="flex items-center gap-2 px-4 py-2 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <component :is="pushLoading === 'descriptions' ? Loader2 : FileText" class="w-4 h-4" :class="{ 'animate-spin': pushLoading === 'descriptions' }" />
              Push Descriptions
            </button>
            <button
              @click="pushToProduction('both')"
              :disabled="pushing"
              class="flex items-center gap-2 px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <component :is="pushLoading === 'both' ? Loader2 : CheckCircle" class="w-4 h-4" :class="{ 'animate-spin': pushLoading === 'both' }" />
              Push Both
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Dialog -->
  <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="cancelDelete">
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Delete Staging Data</h3>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Are you sure you want to delete staging data for
        <span v-if="deleteTargetFileIds.length > 1">{{ deleteTargetFileIds.length }} files</span>
        <span v-else>this file</span>?
      </p>
      
      <!-- Delete Type Selection -->
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Delete:</label>
        <div class="flex gap-2">
          <button
            @click="deleteType = 'tags'"
            :class="deleteType === 'tags' ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
            class="flex-1 px-3 py-2 text-sm rounded-lg transition-colors"
          >
            Tags Only
          </button>
          <button
            @click="deleteType = 'descriptions'"
            :class="deleteType === 'descriptions' ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
            class="flex-1 px-3 py-2 text-sm rounded-lg transition-colors"
          >
            Descriptions Only
          </button>
          <button
            @click="deleteType = 'both'"
            :class="deleteType === 'both' ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'"
            class="flex-1 px-3 py-2 text-sm rounded-lg transition-colors"
          >
            Both
          </button>
        </div>
      </div>
      
      <div class="flex gap-2 justify-end">
        <button
          @click="cancelDelete"
          :disabled="deleting"
          class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          @click="confirmDelete"
          :disabled="deleting"
          class="px-4 py-2 text-sm text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <Loader2 v-if="deleting" class="w-4 h-4 animate-spin" />
          <span v-else>Delete</span>
        </button>
      </div>
    </div>
  </div>
</template>
