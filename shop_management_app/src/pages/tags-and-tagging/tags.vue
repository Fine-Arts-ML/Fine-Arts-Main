<script setup lang="ts">
import { onMounted, computed, ref, watch, reactive } from 'vue'
import { useAuth } from '~/composables/useAuth'
import { useTagPipeline } from '~/composables/useTagPipeline'
import { useImagePreview } from '~/composables/useImagePreview'
import ImagePreviewModal from '~/components/ImagePreviewModal.vue'
import { ChevronDown, ChevronUp, Sparkles, Loader2, ArrowLeft, ArrowRight, Settings2, X, XCircle, Play } from 'lucide-vue-next'

const { isAdmin } = useAuth()
const {
  selectedFileIds,
  selectedFiles,
  generatedTags,
  generatedDescriptions,
  setGeneratedTags,
  setGeneratedDescription,
  removeFileId,
  clearSelection,
} = useTagPipeline()

definePageMeta({
  middleware: 'tags-pipeline',
})

useHead({
  title: 'Tags & Descriptions - Tags & Tagging',
})

interface FileInfo {
  file_id: string
  file_name: string
  file_path: string
  mime_type: string
  is_tagged: boolean
  existing_tags: Array<{ id: number; name: string; color: string }>
  preview_url?: string
}

interface AIModel {
  id: string
  name: string
  object: string
  ownedBy: string
}

// Generation modes: 'tags' | 'descriptions' | 'both'
type GenerationMode = 'tags' | 'descriptions' | 'both'

// State
const scanResults = ref<FileInfo[]>([])
const isGenerating = ref(false)
const isFetchingModels = ref(false)
const availableModels = ref<AIModel[]>([])
const selectedModelId = ref('')
const tagSettingsExpanded = ref(true)
const tagMaxTags = ref(20)
const tagTemperature = ref(0.1)
const tagMaxTokens = ref(3000)
const tagThinkingEnabled = ref(true)
const tagCustomPrompt = ref('')
const activeFileTab = ref(0)
const modelsFetchError = ref('')
const splitButtons = ref<Record<string, boolean>>({})
const generatingFiles = reactive<Record<string, boolean>>({})

// Lazy loading state for file list
const visibleCount = ref(20) // Show 20 files initially
const sentinelRef = ref<HTMLElement | null>(null)
const isObserving = ref(false)

// Expansion state for review data rows (tags, descriptions)
const expandedFiles = ref<Set<string>>(new Set())

// Toggle file row expansion in review section
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

// Image preview
const { open: openPreview, close: closePreview, navigate: navigatePreview, state: previewState } = useImagePreview()

// Track which specific pill is generating for each file: 'tags' | 'description' | null
const generatingPill = ref<Record<string, 'tags' | 'description' | null>>({})

// ========== Staging State ==========
// Staging state: track which files have tags/descriptions staged for database persistence
const stagedTags = ref<Set<string>>(new Set())
const stagedDescriptions = ref<Set<string>>(new Set())
const isStaging = ref(false)

// Computed staging counts
const stagedTagsCount = computed(() => stagedTags.value.size)
const stagedDescriptionsCount = computed(() => stagedDescriptions.value.size)
const hasStagedItems = computed(() => stagedTags.value.size > 0 || stagedDescriptions.value.size > 0)

// Helper to check if a file is currently being generated
function isFileGenerating(fileId: string): boolean {
  return !!generatingFiles[fileId]
}

// Helper to check which pill is generating
function isPillGenerating(fileId: string, pillType: 'tags' | 'description'): boolean {
  return generatingPill.value[fileId] === pillType
}

// Helper to check if any pill is generating for a file (tags OR description)
function isAnyPillGenerating(fileId: string): boolean {
  return !!generatingPill.value[fileId]
}

// Helper to check if a file has tags
function fileHasTags(fileId: string | number): boolean {
  const id = Number(fileId)
  return (generatedTags.value?.get(id)?.length ?? 0) > 0
}

// Helper to check if a file has description
function fileHasDesc(fileId: string | number): boolean {
  const id = Number(fileId)
  return !!generatedDescriptions.value?.get(id)
}

// Get 64x64 preview URL for a file
function getPreviewUrl(fileId: string, mimeType?: string): string | null {
  if (!mimeType || !mimeType.startsWith('image/')) return null
  return `/api/files/preview-proxy/${fileId}?x=64&y=64`
}

// Open full-size preview modal
function openFullPreview(file: FileInfo) {
  const previewUrl = getPreviewUrl(file.file_id, file.mime_type)
  if (previewUrl) {
    openPreview({ fileId: Number(file.file_id), filename: file.file_name, previewUrl: previewUrl.replace('x=64&y=64', 'x=1080&y=1080') })
  }
}

// Check if file is an image
function isImage(mimeType: string): boolean {
  return mimeType.startsWith('image/')
}

// Remove a file from the selection list
function removeFileFromSelection(fileId: string): void {
  removeFileId(fileId)
  // Also clean up generated data for this file
  const numId = Number(fileId)
  if (generatedTags.value?.has(numId)) {
    generatedTags.value.delete(numId)
  }
  if (generatedDescriptions.value?.has(numId)) {
    generatedDescriptions.value.delete(numId)
  }
  // Clean up staging state
  stagedTags.value.delete(fileId)
  stagedDescriptions.value.delete(fileId)
  // Clean up UI state
  expandedFiles.value.delete(fileId)
  const genKey = fileId as unknown as keyof typeof generatingFiles
  delete generatingFiles[genKey]
  const genPillKey = fileId as unknown as keyof typeof generatingPill.value
  generatingPill.value[genPillKey as keyof typeof generatingPill.value] = null
  delete splitButtons.value[fileId]
}

// Clear all files from selection
function clearAllFiles(): void {
  clearSelection()
  generatedTags.value = new Map()
  generatedDescriptions.value = new Map()
  stagedTags.value.clear()
  stagedDescriptions.value.clear()
  expandedFiles.value.clear()
  Object.keys(generatingFiles).forEach(key => delete generatingFiles[key])
  Object.keys(generatingPill.value).forEach(key => generatingPill.value[key] = null)
  Object.keys(splitButtons.value).forEach(key => delete splitButtons.value[key])
}

// Check if a generated tag is a duplicate of an existing tag (case-insensitive string comparison)
function isDuplicateTag(generatedTag: string, existingTags: Array<{ id: number; name: string; color: string }>): boolean {
  const lowerGenerated = generatedTag.toLowerCase().trim()
  return existingTags.some(existing => existing.name.toLowerCase().trim() === lowerGenerated)
}

// ========== Staging Helper Functions ==========
function isTagStaged(fileId: string): boolean {
  return stagedTags.value.has(fileId)
}

function isDescriptionStaged(fileId: string): boolean {
  return stagedDescriptions.value.has(fileId)
}

// Build tags object for API: { "fileId": ["tag1", "tag2"] }
function buildTagsObject(): Record<string, string[]> {
  const tagsObj: Record<string, string[]> = {}
  for (const file of selectedFilesList.value) {
    const fileId = file.file_id
    const fileIdNum = Number(fileId)
    const tags = generatedTags.value?.get(fileIdNum)
    if (tags && tags.length > 0) {
      tagsObj[fileId] = tags.map((t: any) => t.name)
    }
  }
  return tagsObj
}

// Build descriptions object for API: { "fileId": "description text" }
function buildDescriptionsObject(): Record<string, string> {
  const descObj: Record<string, string> = {}
  for (const file of selectedFilesList.value) {
    const fileId = file.file_id
    const fileIdNum = Number(fileId)
    const desc = generatedDescriptions.value?.get(fileIdNum)
    if (desc) {
      descObj[fileId] = desc
    }
  }
  return descObj
}

async function stageTagsToDb(tagsObj: Record<string, string[]>, descObj: Record<string, string>): Promise<boolean> {
  try {
    await $fetch('/api/settings/rag-index/staging/push', {
      method: 'POST',
      body: { tags: tagsObj, descriptions: descObj },
    })
    return true
  } catch (error: any) {
    console.error('[STAGE] Failed to stage data:', error)
    return false
  }
}

async function stageTags(fileId: string): Promise<void> {
  const tagsObj = buildTagsObject()
  const descObj = buildDescriptionsObject()
  const success = await stageTagsToDb(tagsObj, descObj)
  if (success) {
    stagedTags.value.add(fileId)
    console.log('[STAGE] Staged tags for file:', fileId)
  }
}

async function stageDescription(fileId: string): Promise<void> {
  const tagsObj = buildTagsObject()
  const descObj = buildDescriptionsObject()
  const success = await stageTagsToDb(tagsObj, descObj)
  if (success) {
    stagedDescriptions.value.add(fileId)
    console.log('[STAGE] Staged description for file:', fileId)
  }
}

function unstageTags(fileId: string): void {
  stagedTags.value.delete(fileId)
}

function unstageDescription(fileId: string): void {
  stagedDescriptions.value.delete(fileId)
}

// Bulk staging functions
async function stageAllTags(): Promise<void> {
  if (isStaging.value) return
  isStaging.value = true
  try {
    const tagsObj = buildTagsObject()
    const descObj = buildDescriptionsObject()
    const success = await stageTagsToDb(tagsObj, descObj)
    if (success) {
      for (const file of selectedFilesList.value) {
        if (fileHasTags(file.file_id)) {
          stagedTags.value.add(file.file_id)
        }
      }
      console.log('[STAGE] Staged all tags:', stagedTags.value.size, 'files')
    }
  } finally {
    isStaging.value = false
  }
}

async function stageAllDescriptions(): Promise<void> {
  if (isStaging.value) return
  isStaging.value = true
  try {
    const tagsObj = buildTagsObject()
    const descObj = buildDescriptionsObject()
    const success = await stageTagsToDb(tagsObj, descObj)
    if (success) {
      for (const file of selectedFilesList.value) {
        if (fileHasDesc(file.file_id)) {
          stagedDescriptions.value.add(file.file_id)
        }
      }
      console.log('[STAGE] Staged all descriptions:', stagedDescriptions.value.size, 'files')
    }
  } finally {
    isStaging.value = false
  }
}

async function stageAll(): Promise<void> {
  if (isStaging.value) return
  isStaging.value = true
  try {
    const tagsObj = buildTagsObject()
    const descObj = buildDescriptionsObject()
    const success = await stageTagsToDb(tagsObj, descObj)
    if (success) {
      for (const file of selectedFilesList.value) {
        if (fileHasTags(file.file_id)) {
          stagedTags.value.add(file.file_id)
        }
        if (fileHasDesc(file.file_id)) {
          stagedDescriptions.value.add(file.file_id)
        }
      }
      console.log('[STAGE] Staged all:', stagedTags.value.size, 'tags,', stagedDescriptions.value.size, 'descriptions')
    }
  } finally {
    isStaging.value = false
  }
}

function clearStaging(): void {
  stagedTags.value.clear()
  stagedDescriptions.value.clear()
}

// Generation progress state
const generationMode = ref<GenerationMode>('both')
const generationProgress = ref<{ current: number; total: number } | null>(null)
const isAborting = ref(false)
const abortController = ref<AbortController | null>(null)

const DEFAULT_TAG_SYSTEM_PROMPT = `You are an expert art tagging assistant. Analyze the provided image and return relevant tags for cataloging artwork and photographs.
- Generate tags considering: subject matter, artistic style, medium, colors, composition, lighting, mood, technique
- Tags should be specific, descriptive, and in English
- Include both broad categories and specific details`
const SYTSTEM_PROMPT_FORMAT_INSTRUCT = `
\nOutput Format instructions:
\nUse lowercase for all tags
\nUse multi-word tags separated by spaces (e.g., "oil painting", "landscape view")
\nReturn tags as a semicolon-separated list ONLY`

// Computed
const selectedFilesList = computed(() => {
  console.log('tags.vue: selectedFiles from composable:', selectedFiles.value)
  if (selectedFiles.value && selectedFiles.value.length > 0) {
    return selectedFiles.value as FileInfo[]
  }
  return [] as FileInfo[]
})

const hasSelectedFiles = computed(() => selectedFileIds.value.length > 0)

const activeFile = computed(() => {
  if (selectedFilesList.value.length === 0) return null
  return selectedFilesList.value[activeFileTab.value] || selectedFilesList.value[0]
})

const activeFileTags = computed(() => {
  if (!activeFile.value) return []
  const fileId = Number(activeFile.value.file_id)
  return generatedTags.value?.get(fileId) || []
})

const activeFileDescription = computed(() => {
  if (!activeFile.value) return ''
  const fileId = Number(activeFile.value.file_id)
  return generatedDescriptions.value?.get(fileId) || ''
})

const activeFileExistingTags = computed(() => {
  if (!activeFile.value) return []
  return activeFile.value.existing_tags?.map((t: any) => t.name) || []
})

const totalFiles = computed(() => selectedFilesList.value.length)

const hasGeneratedForActiveFile = computed(() => {
  if (!activeFile.value) return false
  const fileId = Number(activeFile.value.file_id)
  const hasTags = (generatedTags.value?.get(fileId)?.length ?? 0) > 0
  const hasDesc = generatedDescriptions.value?.get(fileId)
  return hasTags || hasDesc
})

const progressPercentage = computed(() => {
  if (!generationProgress.value) return 0
  return Math.round((generationProgress.value.current / generationProgress.value.total) * 100)
})

// Lazy loading: Get the subset of files to render based on visibleCount
const visibleFiles = computed(() => {
  return selectedFilesList.value.slice(0, visibleCount.value)
})

// Check if there are more files to load
const hasMoreFiles = computed(() => {
  return visibleCount.value < selectedFilesList.value.length
})

// Check if a specific file has generated tags or description
function hasGeneratedForFile(fileId: string | number): boolean {
  const id = Number(fileId)
  const hasTags = (generatedTags.value?.get(id)?.length ?? 0) > 0
  const hasDesc = generatedDescriptions.value?.get(id)
  return hasTags || hasDesc
}

// Methods
async function fetchAvailableModels() {
  isFetchingModels.value = true
  try {
    const result = await $fetch('/api/settings/rag-index/available-models', { method: 'GET' })
    if (result?.success && result.models) {
      availableModels.value = result.models
      if (availableModels.value.length > 0 && !selectedModelId.value) {
        selectedModelId.value = availableModels.value[0].id
      }
    }
  } catch (error: any) {
    modelsFetchError.value = error.message || 'Failed to fetch models'
  } finally {
    isFetchingModels.value = false
  }
}

async function generateTagsForFile(fileId: string) {
  generatingPill.value[fileId] = 'tags'
  try {
    const result = await $fetch('/api/settings/rag-index/generate-tags-direct', {
      method: 'POST',
      body: {
        file_ids: [fileId],
        max_tags: tagMaxTags.value,
        temperature: tagTemperature.value,
        max_tokens: tagMaxTokens.value,
        thinking_enabled: tagThinkingEnabled.value,
        custom_prompt: tagCustomPrompt.value + SYTSTEM_PROMPT_FORMAT_INSTRUCT || DEFAULT_TAG_SYSTEM_PROMPT + SYTSTEM_PROMPT_FORMAT_INSTRUCT
      }
    })
    
    if (result?.results) {
      for (const [fid, data] of Object.entries(result.results)) {
        const tagData = data as { tags: string[]; success: boolean }
        if (tagData.success && tagData.tags) {
          const tagInfoArray = tagData.tags.map((tagName: string, index: number) => ({
            id: Number(fid) + index,
            name: tagName,
            num_files: 0,
          }))
          setGeneratedTags(Number(fid), tagInfoArray)
        }
      }
    }
  } catch (error: any) {
    console.error('Failed to generate tags:', error)
    throw error
  } finally {
    generatingPill.value[fileId] = null
    splitButtons.value[fileId] = false
  }
}

async function generateDescriptionForFile(fileId: string) {
  generatingPill.value[fileId] = 'description'
  try {
    const result = await $fetch('/api/settings/rag-index/generate-descriptions', {
      method: 'POST',
      body: {
        file_ids: [fileId]
      }
    })
    
    if (result?.results) {
      for (const [fid, data] of Object.entries(result.results)) {
        const descData = data as { description: string; success: boolean }
        if (descData.success && descData.description) {
          setGeneratedDescription(Number(fid), descData.description)
        }
      }
    }
  } catch (error: any) {
    console.error('Failed to generate description:', error)
    throw error
  } finally {
    generatingPill.value[fileId] = null
    splitButtons.value[fileId] = false
  }
}

async function generateForFile(fileId: string) {
  if (generatingFiles[fileId]) return
  
  generatingFiles[fileId] = true
  
  try {
    await generateTagsForFile(fileId)
    await generateDescriptionForFile(fileId)
  } catch (error: any) {
    console.error(`Failed to process file ${fileId}:`, error)
  } finally {
    generatingFiles[fileId] = false
  }
}

async function generateForActiveFile(mode: GenerationMode) {
  if (!activeFile.value || isGenerating.value) return
  
  isGenerating.value = true
  generationProgress.value = { current: 1, total: 1 }
  
  try {
    if (mode === 'tags' || mode === 'both') {
      await generateTagsForFile(activeFile.value.file_id)
    }
    if (mode === 'descriptions' || mode === 'both') {
      await generateDescriptionForFile(activeFile.value.file_id)
    }
  } catch (error: any) {
    console.error('Generation failed:', error)
  } finally {
    isGenerating.value = false
    generationProgress.value = null
  }
}

async function generateForAllFiles(mode: GenerationMode) {
  if (!hasSelectedFiles.value || isGenerating.value) return
  
  isGenerating.value = true
  isAborting.value = false
  abortController.value = new AbortController()
  generationProgress.value = { current: 0, total: selectedFilesList.value.length }
  
  const fileIds = selectedFilesList.value.map(f => f.file_id)
  
  try {
    for (let i = 0; i < fileIds.length; i++) {
      if (isAborting.value) {
        console.log('Generation aborted by user')
        break
      }
      
      generationProgress.value = { current: i + 1, total: fileIds.length }
      const fileId = fileIds[i]
      
      try {
        if (mode === 'tags' || mode === 'both') {
          await generateTagsForFile(fileId)
        }
        if (mode === 'descriptions' || mode === 'both') {
          await generateDescriptionForFile(fileId)
        }
      } catch (error: any) {
        console.error(`Failed to process file ${fileId}:`, error)
      }
    }
  } finally {
    isGenerating.value = false
    generationProgress.value = null
    abortController.value = null
  }
}

function handleAbort() {
  isAborting.value = true
  if (abortController.value) {
    abortController.value.abort()
  }
}

function formatDate(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleDateString()
}

// Lazy loading: Intersection Observer to load more files on scroll
function setupLazyLoadingObserver(): void {
  if (isObserving.value) return
  
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && visibleCount.value < selectedFilesList.value.length) {
          // Load next batch of 20 files
          visibleCount.value = Math.min(visibleCount.value + 20, selectedFilesList.value.length)
        }
      })
    },
    {
      root: null, // Use viewport as root
      rootMargin: '200px', // Start loading 200px before element is visible
      threshold: 0,
    }
  )
  
  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
    isObserving.value = true
  }
}

function cleanupLazyLoadingObserver(): void {
  isObserving.value = false
}

onMounted(() => {
  fetchAvailableModels()
})

// Watch for changes to selectedFilesList to reset lazy loading state
watch(selectedFilesList, () => {
  visibleCount.value = 20
  cleanupLazyLoadingObserver()
  // Use nextTick to ensure DOM is updated before setting up observer
  setTimeout(() => setupLazyLoadingObserver(), 100)
}, { deep: false })
</script>

<template>
  <div class="space-y-6">
    <!-- Settings Panel -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button @click="tagSettingsExpanded = !tagSettingsExpanded" class="w-full p-4 flex items-center justify-between bg-gradient-to-r from-purple-900/30 to-blue-900/20 dark:from-purple-900/40 dark:to-blue-900/30 hover:from-purple-900/40 hover:to-blue-900/30 transition-colors">
        <div class="flex items-center gap-2">
          <Settings2 class="w-5 h-5 text-purple-500 dark:text-purple-400" />
          <span class="font-medium text-gray-900 dark:text-gray-100">Tag Generation Settings</span>
          <span v-if="hasSelectedFiles" class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 rounded-full">{{ totalFiles }} files selected</span>
        </div>
        <component :is="tagSettingsExpanded ? ChevronUp : ChevronDown" class="w-5 h-5 text-purple-500 dark:text-purple-400" />
      </button>
      
      <div v-if="tagSettingsExpanded" class="p-4 border-t border-gray-200 dark:border-gray-700 space-y-5">
        <!-- Max Tags per Picture - Full Width Slider -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Max Tags per Picture: <span class="text-purple-600 dark:text-purple-400">{{ tagMaxTags }}</span>
          </label>
          <input v-model.number="tagMaxTags" type="range" min="1" max="100" class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600" />
          <div class="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            <span>100</span>
          </div>
        </div>

        <!-- AI Model - Full Width Dropdown -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">AI Model</label>
          <div v-if="isFetchingModels" class="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 class="w-4 h-4 animate-spin" /> Loading models...
          </div>
          <div v-else-if="modelsFetchError" class="text-sm text-red-500">{{ modelsFetchError }}</div>
          <select v-else v-model="selectedModelId" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            <option value="">Use Default Model</option>
            <option v-for="model in availableModels" :key="model.id" :value="model.id">{{ model.name }}</option>
          </select>
          <p v-if="!selectedModelId && !isFetchingModels && !modelsFetchError" class="text-xs text-gray-500 mt-1">No models available. Check AI endpoint configuration.</p>
        </div>

        <!-- Model Temperature - Full Width Slider -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Model Temperature: <span class="text-purple-600 dark:text-purple-400">{{ tagTemperature }}</span>
          </label>
          <input v-model.number="tagTemperature" type="range" min="0" max="2" step="0.1" class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600" />
          <div class="flex justify-between text-xs text-gray-500 mt-1">
            <span>0 (precise)</span>
            <span>2 (creative)</span>
          </div>
        </div>

        <!-- Max Tokens - Full Width Input -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Max Tokens: <span class="text-purple-600 dark:text-purple-400">{{ tagMaxTokens }}</span>
          </label>
          <input v-model.number="tagMaxTokens" type="number" min="50" max="60000" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100" />
          <p class="text-xs text-gray-500 mt-1">3000 tokens is usually enough for 10-20 detailed tags, but you need to increase the limit if you want more tags per file.</p>
        </div>

        <!-- Enable Thinking - Full Width Toggle -->
        <div>
          <label class="flex items-center justify-between cursor-pointer">
            <div>
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Enable Thinking</span>
              <p class="text-xs text-gray-500 mt-0.5">Use extended reasoning for better tags</p>
            </div>
            <button
              @click="tagThinkingEnabled = !tagThinkingEnabled"
              :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors', tagThinkingEnabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600']"
            >
              <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform', tagThinkingEnabled ? 'translate-x-6' : 'translate-x-1']" />
            </button>
          </label>
        </div>

        <!-- Custom Prompt - Full Width Textarea -->
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Custom Prompt (optional - leave empty for default)</label>
          <textarea v-model="tagCustomPrompt" rows="6" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-y" :placeholder="DEFAULT_TAG_SYSTEM_PROMPT" />
          <p class="text-xs text-gray-500 mt-1">The system will append image analysis instructions to your prompt.</p>
        </div>
      </div>
    </div>

    

    <!-- Files List (matching screenshot layout) -->
    <div v-if="selectedFilesList.length > 0" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">

    <!-- Generation Mode Buttons & Progress Bar -->
    <div v-if="hasSelectedFiles" class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 overflow-hidden">
      <!-- Mode Selection Buttons (shown when not generating) -->
      <div v-if="!isGenerating" class="p-4">
        <!-- Generate button with hover-reveal menu -->
        <div class="relative group">
          <!-- Main button - fades out on hover, replaced by menu -->
          <button
            class="generate-main-btn w-full px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 shadow-md"
          >
            <Sparkles class="w-4 h-4" />
            Generate ({{ totalFiles }})
          </button>
          
          <!-- Hover menu - fades in on hover, REPLACES the button in the same space -->
          <div class="hover-menu absolute inset-0 flex items-center gap-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
            <!-- Generate All (Tags + Descriptions) -->
            <button
              @click="generateForAllFiles('both')"
              :disabled="isGenerating || !hasSelectedFiles"
              class="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-1.5 bg-gradient-to-r from-purple-500 to-blue-500 text-white hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              <Sparkles class="w-4 h-4" />
              Generate All
            </button>
            
            <!-- Generate Tags Only -->
            <button
              @click="generateForAllFiles('tags')"
              :disabled="isGenerating || !hasSelectedFiles"
              class="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-1.5 bg-purple-500 text-white hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              <Sparkles class="w-4 h-4" />
              Tags Only
            </button>
            
            <!-- Generate Descriptions Only -->
            <button
              @click="generateForAllFiles('descriptions')"
              :disabled="isGenerating || !hasSelectedFiles"
              class="flex-1 px-4 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-1.5 bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              <Sparkles class="w-4 h-4" />
              Desc Only
            </button>
          </div>
        </div>
      </div>
      
      <!-- Progress Bar (shown when generating) -->
      <div v-else class="p-4">
        <div
          class="group relative h-10 rounded-lg overflow-hidden bg-gradient-to-r from-purple-500 to-blue-500 shadow-md cursor-pointer"
        >
          <!-- Background gradient (always visible) -->
          <div class="absolute inset-0 bg-gradient-to-r from-purple-500 to-blue-500"></div>
          
          <!-- Progress fill overlay -->
          <div
            class="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 transition-all duration-300"
            :style="{ width: generationProgress ? `${progressPercentage}%` : '0%' }"
          ></div>
          
          <!-- Animated shimmer overlay - flows left to right -->
          <div
            v-if="isGenerating"
            class="absolute inset-0 shimmer-overlay"
          ></div>
          
          <!-- Hover overlay - uses CSS group-hover for reliable hover detection -->
          <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none">
            <button
              @click.stop="handleAbort"
              class="w-full h-full bg-red-500/90 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-red-600 transition-colors cursor-pointer"
            >
              <XCircle class="w-4 h-4" />
              Abort Generation
            </button>
          </div>
          
          <!-- Progress text overlay (hidden when hovering) -->
          <Transition name="fade" mode="out-in">
            <div v-if="generationProgress && !isAborting" class="absolute inset-0 flex items-center justify-center group-hover:opacity-0 transition-opacity duration-200">
              <span class="text-xs font-medium text-white bg-black/30 px-2 py-0.5 rounded">
                {{ generationProgress.current }} / {{ generationProgress.total }}
              </span>
            </div>
          </Transition>
        </div>
      </div>
    </div>
      <!-- Section Header -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-red-500">⊙</span>
          <h3 class="font-medium text-gray-900 dark:text-gray-100">Files Without Tags ({{ selectedFilesList.length }})</h3>
        </div>
           <button
            v-if="hasSelectedFiles"
            @click="clearAllFiles"
            class="ml-2 px-2 py-0.5 bg-red-500/10 text-red-600 dark:text-red-400 text-xs font-medium rounded-full hover:bg-red-500/20 flex items-center gap-1"
            title="Clear all files from selection">
          <X class="w-3 h-3" />
            Clear All
          </button>
      </div>
      <!-- Bulk Staging Row -->
      <div v-if="hasSelectedFiles" class="px-4 py-3 dark:border-gray-700 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-end gap-2">
          <button
            @click="stageAllTags"
            :disabled="!hasSelectedFiles || isStaging"
            class="px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <Loader2 v-if="isStaging" class="w-3 h-3 animate-spin" />
            <Sparkles v-else class="w-3 h-3" />
            Stage All Tags
          </button>
          <button
            @click="stageAllDescriptions"
            :disabled="!hasSelectedFiles || isStaging"
            class="px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <Loader2 v-if="isStaging" class="w-3 h-3 animate-spin" />
            <Sparkles v-else class="w-3 h-3" />
            Stage All Descriptions
          </button>
          <button
            @click="stageAll"
            :disabled="!hasSelectedFiles || isStaging"
            class="px-3 py-1.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-medium rounded-full hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <Loader2 v-if="isStaging" class="w-3 h-3 animate-spin" />
            <Sparkles v-else class="w-3 h-3" />
            Stage All
          </button>
          <button
            v-if="hasStagedItems"
            @click="clearStaging"
            class="px-3 py-1.5 bg-gray-500 text-white text-xs font-medium rounded-full hover:bg-gray-600 flex items-center gap-1"
          >
            <X class="w-3 h-3" />
            Clear Staging
          </button>
        </div>
      </div>
      <!-- File List Items (Lazy Loaded) -->
      <div class="divide-y divide-gray-200 dark:divide-gray-700">
        <div
          v-for="file in visibleFiles"
          :key="file.file_id"
          class="p-4 space-y-3"
        >
          <!-- File Header Row (always visible) -->
          <div class="flex items-center gap-3">
            <!-- Expand/Collapse Chevron -->
            <button
              @click.stop="toggleFileExpansion(file.file_id)"
              class="flex-shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            >
              <ChevronUp v-if="isFileExpanded(file.file_id)" class="w-4 h-4" />
              <ChevronDown v-else class="w-4 h-4" />
            </button>

            <!-- Thumbnail Preview -->
            <div v-if="isImage(file.mime_type)" class="flex-shrink-0">
              <img
                :src="getPreviewUrl(file.file_id, file.mime_type)!"
                :alt="file.file_name"
                class="w-16 h-16 rounded object-cover border border-gray-200 dark:border-gray-700 cursor-pointer hover:opacity-80 transition-opacity"
                @click.stop="openFullPreview(file)"
                loading="lazy"
              />
            </div>
            
            <!-- File Info -->
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ file.file_name }}</h4>
              <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{{ file.file_path }}</p>
            </div>
            
            <!-- Remove File Button -->
            <button
              @click.stop="removeFileFromSelection(file.file_id)"
              class="flex-shrink-0 p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
              title="Remove file from selection"
            >
              <X class="w-4 h-4" />
            </button>
            
            <!-- Action Buttons Area: Two-row layout (hidden during any generation for this file) -->
            <div v-if="!isFileGenerating(file.file_id) && !isAnyPillGenerating(file.file_id)" class="ml-4 flex flex-col items-end gap-1.5">
              
              <!-- Row 1: Staging Pills Only (shown when content has been generated) -->
              <div v-if="fileHasTags(file.file_id) || fileHasDesc(file.file_id)" class="flex items-center gap-2 flex-wrap justify-end">
                <!-- Staged Tags Indicator -->
                <div v-if="isTagStaged(file.file_id)" class="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs rounded-full flex items-center gap-1">
                  <span>✓ Staged</span>
                  <button @click.stop="unstageTags(file.file_id)" class="ml-0.5 hover:text-amber-900 dark:hover:text-amber-100">
                    <X class="w-3 h-3" />
                  </button>
                </div>
                
                <!-- Stage Tags Pill (shown when tags exist but not staged) -->
                <button
                  v-if="!isTagStaged(file.file_id) && fileHasTags(file.file_id)"
                  @click="stageTags(file.file_id)"
                  class="px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full hover:bg-amber-600 flex items-center gap-1"
                >
                  <Sparkles class="w-3 h-3" />
                  Stage Tags
                </button>
                
                <!-- Staged Description Indicator -->
                <div v-if="isDescriptionStaged(file.file_id)" class="px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs rounded-full flex items-center gap-1">
                  <span>✓ Staged</span>
                  <button @click.stop="unstageDescription(file.file_id)" class="ml-0.5 hover:text-amber-900 dark:hover:text-amber-100">
                    <X class="w-3 h-3" />
                  </button>
                </div>
                
                <!-- Stage Description Pill (shown when description exists but not staged) -->
                <button
                  v-if="!isDescriptionStaged(file.file_id) && fileHasDesc(file.file_id)"
                  @click="stageDescription(file.file_id)"
                  class="px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full hover:bg-amber-600 flex items-center gap-1"
                >
                  <Sparkles class="w-3 h-3" />
                  Stage Description
                </button>
              </div>
              
              <!-- Row 2: Main Action Button (collapsed) or Split Generate Pills (expanded) -->
              <!-- State 1: Nothing generated yet - Purple "Generate Classifications" -->
              <template v-if="!fileHasTags(file.file_id) && !fileHasDesc(file.file_id)">
                <!-- Collapsed state: Single purple button -->
                <button
                  v-if="!splitButtons[file.file_id]"
                  @click="splitButtons[file.file_id] = true"
                  :disabled="!hasSelectedFiles"
                  class="px-4 py-1.5 bg-gradient-to-r from-purple-500 to-blue-500 text-white text-xs font-medium rounded-full hover:from-purple-600 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-md"
                >
                  <Sparkles class="w-3 h-3" />
                  Generate Classifications
                </button>
                
                <!-- Expanded state: Split pills in Row 2, Re-Generate pill stays in Row 2 -->
                <template v-else>
                  <div class="flex items-center gap-2 flex-wrap justify-end">
                    <!-- Generate Tags pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'tags')"
                      disabled
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateTagsForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Tags
                    </button>
                    <!-- Generate Description pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'description')"
                      disabled
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateDescriptionForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Description
                    </button>
                  </div>
                </template>
              </template>
              
              <!-- State 2: Only tags OR only description generated - Yellow "Re-Generate Classification" -->
              <template v-else-if="(fileHasTags(file.file_id) && !fileHasDesc(file.file_id)) || (!fileHasTags(file.file_id) && fileHasDesc(file.file_id))">
                <!-- Collapsed state: Single yellow button -->
                <button
                  v-if="!splitButtons[file.file_id]"
                  @click="splitButtons[file.file_id] = true"
                  :disabled="!hasSelectedFiles"
                  class="px-4 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-full hover:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-md"
                >
                  <Sparkles class="w-3 h-3" />
                  Re-Generate Classification
                </button>
                
                <!-- Expanded state: Split pills in Row 2 -->
                <template v-else>
                  <div class="flex items-center gap-2 flex-wrap justify-end">
                    <!-- Generate Tags pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'tags')"
                      disabled
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateTagsForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Tags
                    </button>
                    <!-- Generate Description pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'description')"
                      disabled
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateDescriptionForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Description
                    </button>
                  </div>
                </template>
              </template>
              
              <!-- State 3: Both tags AND description generated - Green "Re-Generate Classification" -->
              <template v-else>
                <!-- Collapsed state: Single green button -->
                <button
                  v-if="!splitButtons[file.file_id]"
                  @click="splitButtons[file.file_id] = true"
                  :disabled="!hasSelectedFiles"
                  class="px-4 py-1.5 bg-green-500 text-white text-xs font-medium rounded-full hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5 shadow-md"
                >
                  <Sparkles class="w-3 h-3" />
                  Re-Generate Classification
                </button>
                
                <!-- Expanded state: Split pills in Row 2 -->
                <template v-else>
                  <div class="flex items-center gap-2 flex-wrap justify-end">
                    <!-- Generate Tags pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'tags')"
                      disabled
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateTagsForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-purple-500 text-white text-xs font-medium rounded-full hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Tags
                    </button>
                    <!-- Generate Description pill with animation when generating -->
                    <button
                      v-if="isPillGenerating(file.file_id, 'description')"
                      disabled
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full flex items-center gap-1.5 animate-shimmer"
                    >
                      <Loader2 class="w-3 h-3 animate-spin" />
                      Generating...
                    </button>
                    <button
                      v-else
                      @click="generateDescriptionForFile(file.file_id)"
                      :disabled="!hasSelectedFiles"
                      class="px-3 py-1.5 bg-blue-500 text-white text-xs font-medium rounded-full hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                      <Sparkles class="w-3 h-3" />
                      Generate Description
                    </button>
                  </div>
                </template>
              </template>
            </div>
            
            <!-- Per-file Generating spinner (shown when any generation is in progress for this file) -->
            <button
              v-if="isFileGenerating(file.file_id) || isAnyPillGenerating(file.file_id)"
              disabled
              class="ml-4 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-500 text-xs font-medium rounded-full flex items-center gap-1"
            >
              <Loader2 class="w-3 h-3 animate-spin" />
              Generating...
            </button>
              
          </div>
          
          <!-- Collapsible Review Data Section (only visible when expanded) -->
          <div v-if="isFileExpanded(file.file_id)" class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
            <!-- AI Generated Tags -->
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">AI Generated Tags:</label>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="tag in (generatedTags?.get(Number(file.file_id)) || [])"
                  :key="tag.id"
                  :class="file.existing_tags && isDuplicateTag(tag.name, file.existing_tags)
                    ? 'px-2 py-1 bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs rounded-full border border-amber-300 dark:border-amber-700'
                    : 'px-2 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 text-xs rounded-full'"
                  :title="file.existing_tags && isDuplicateTag(tag.name, file.existing_tags) ? 'Duplicate of existing tag' : ''"
                >
                  {{ tag.name }}
                </span>
                <span v-if="(generatedTags?.get(Number(file.file_id)) || []).length === 0" class="text-xs text-gray-500 italic">
                  No tags generated yet
                </span>
              </div>
            </div>
            
            <!-- Generated Description -->
            <div>
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Description:</label>
              <div v-if="generatedDescriptions?.get(Number(file.file_id))" class="p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-xs text-gray-700 dark:text-gray-300 leading-relaxed">
                {{ generatedDescriptions.get(Number(file.file_id)) }}
              </div>
              <p v-else class="text-xs text-gray-500 italic">No description generated yet</p>
            </div>
            
            <!-- Original Tags (if any) -->
            <div v-if="file.existing_tags && file.existing_tags.length > 0">
              <label class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1.5">Original Tags:</label>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="tag in file.existing_tags"
                  :key="tag.id"
                  class="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-xs rounded"
                >
                  {{ tag.name }}
                </span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Loading Sentinel: Intersection Observer target for lazy loading -->
        <div
          v-if="hasMoreFiles"
          ref="sentinelRef"
          class="p-4 text-center"
        >
          <div class="text-xs text-gray-400 dark:text-gray-500">
            Loading more files...
          </div>
        </div>
      </div>
      
      <!-- Loading Status Footer -->
      <div v-if="selectedFilesList.length > 20" class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <div class="text-xs text-gray-500 dark:text-gray-400 text-center">
          Showing {{ visibleFiles.length }} of {{ selectedFilesList.length }} files
          <span v-if="hasMoreFiles" class="ml-2">(scroll to load more)</span>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
      <Sparkles class="w-12 h-12 text-gray-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No Files Selected</h3>
      <p class="text-gray-500 dark:text-gray-400 mb-4">Please select files in the Scan Files step first.</p>
      <NuxtLink to="/tags-and-tagging/scan-files" class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        <ArrowLeft class="w-4 h-4" />
        Go to Scan Files
      </NuxtLink>
    </div>

    <!-- Navigation -->
    <div class="flex justify-between">
      <NuxtLink to="/tags-and-tagging/scan-files" class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 flex items-center gap-2">
        <ArrowLeft class="w-4 h-4" />
        Back to Scan Files
      </NuxtLink>
      <NuxtLink to="/tags-and-tagging/review-data" :class="['px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2', generatedTags?.size === 0 ? 'opacity-50 cursor-not-allowed' : '']">
        Next: Apply Tags
        <ArrowRight class="w-4 h-4" />
      </NuxtLink>
    </div>
  </div>

  <!-- Image Preview Modal -->
  <ImagePreviewModal :state="previewState" :close="closePreview" :navigate="navigatePreview" />
</template>

<style scoped>
@keyframes shimmerFlow {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.animate-shimmer {
  background: linear-gradient(90deg, var(--tw-gradient-stops));
  background-image: linear-gradient(90deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.4) 50%, rgba(255,255,255,0.1) 100%);
  background-size: 200% 100%;
  animation: shimmerFlow 1.5s linear infinite;
}

/* Progress bar shimmer overlay - flows left to right with visible white pulse */
.shimmer-overlay {
  background-image: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.15) 20%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.15) 80%,
    rgba(255, 255, 255, 0) 100%
  );
  background-size: 200% 100%;
  animation: shimmerFlow 1.5s ease-in-out infinite;
  z-index: 1;
  pointer-events: none;
}

/* Generate button fade transition - fades out when hovering over parent */
.generate-main-btn {
  transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
}

.group:hover .generate-main-btn {
  opacity: 0;
  transform: translateY(-4px);
}

/* Hover menu fade transition */
.hover-menu {
  transition: opacity 0.2s ease-in-out, transform 0.2s ease-in-out;
}
</style>
