<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  Search, X, Plus, Image as ImageIcon, Loader2, Pencil,
  ChevronRight, Folder, FolderOpen,
  ArrowUp, ArrowDown, ArrowLeftRight,
} from 'lucide-vue-next'
import Button from '../ui/Button.vue'
import Input from '../ui/Input.vue'
import ImagePreviewModal from '../ImagePreviewModal.vue'
import FileBrowserTree, { type AccessibleFolder } from '../FileBrowserTree.vue'
import CaptionSelectorPanel from './CaptionSelectorPanel.vue'
import { useImagePreview } from '~/composables/useImagePreview'
import type { GalleryImage, GalleryImageCaption } from '~/composables/useGalleries'

interface Props {
  galleryId: number
  galleryName: string
  currentImages: GalleryImage[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:images': [images: GalleryImage[]]
  'close': []
}>()

const { state: previewState, open: openPreview, close: closePreview } = useImagePreview()

// Caption Selector Panel state
const showCaptionSelector = ref(false)
const selectedCaptionImage = ref<{
  imageId: number
  fileId: number
  fileName: string
  captions: GalleryImageCaption[]
} | null>(null)

function openCaptionSelector(image: GalleryImage) {
  selectedCaptionImage.value = {
    imageId: image.id,
    fileId: image.fileId,
    fileName: image.fileName || `File ${image.fileId}`,
    captions: image.captions || [],
  }
  showCaptionSelector.value = true
}

function handleCaptionsUpdate(captions: GalleryImageCaption[]) {
  if (!selectedCaptionImage.value) return
  const img = galleryImages.value.find((i: any) => i.id === selectedCaptionImage.value!.imageId)
  if (img) {
    img.captions = captions
  }
}

// View mode: 'tree' or 'cards'
const viewMode = ref<'tree' | 'cards'>('tree')

// Search
const searchQuery = ref('')

// Tree view - selected file IDs from FileBrowserTree (numeric IDs from oc_filecache.fileid)
const treeSelectedFileIds = ref<Set<number>>(new Set())

// Card view state
const cardSelectedFiles = ref<Set<number>>(new Set())
const cardImages = ref<Array<{ fileId: number; fileName: string; previewUrl?: string }>>([])
const cardLoading = ref(false)
const cardHasMore = ref(true)
const cardOffset = ref(0)
const CARD_LIMIT = 48

// Right panel (gallery images) state
const galleryImages = ref([...props.currentImages])
const captionEdits = ref<Record<number, string>>({})

// Drag state
const draggedFileId = ref<number | null>(null)

// Computed
const selectedCount = computed(() => {
  if (viewMode.value === 'tree') {
    return treeSelectedFileIds.value.size
  }
  return cardSelectedFiles.value.size
})

// Dragged file ID for adding to gallery (from tree or card)
const draggedTreeFileId = ref<string | null>(null)
const draggedCardFileId = ref<number | null>(null)

function getPreviewUrl(fileId: number, size: number = 32): string {
  return `/api/files/preview-proxy/${fileId}?size=${size}`
}

// Tree view handler - called when selection changes in FileBrowserTree (receives numeric file IDs)
function handleTreeSelectionChange(fileIds: Set<number>) {
  treeSelectedFileIds.value = new Set(fileIds)
  console.log('[ImageAssignmentPanel] handleTreeSelectionChange - received file IDs:', Array.from(fileIds))
}

// Card view functions - load images from API
async function loadCardImages(append: boolean = false) {
  if (cardLoading.value) return
  
  cardLoading.value = true
  try {
    const offset = append ? cardOffset.value : 0
    const response = await $fetch<Array<{ fileId: number; filename: string; previewUrl?: string }>>(
      `/api/files/browse-all?limit=${CARD_LIMIT}&offset=${offset}&sortBy=name&sortOrder=asc`
    )
    
    if (!append) {
      cardImages.value = []
      cardOffset.value = 0
    }
    
    // Apply search filter
    const filtered = response.filter(item => {
      if (!searchQuery.value) return true
      return item.filename.toLowerCase().includes(searchQuery.value.toLowerCase())
    })
    
    cardImages.value.push(...filtered)
    cardOffset.value += filtered.length
    cardHasMore.value = filtered.length >= CARD_LIMIT
  } catch (e: any) {
    console.error('Failed to load images:', e)
  } finally {
    cardLoading.value = false
  }
}

function handleCardScroll(event: Event) {
  const target = event.target as HTMLElement
  const { scrollTop, scrollHeight, clientHeight } = target
  if (scrollHeight - scrollTop - clientHeight < 100) {
    if (cardHasMore.value && !cardLoading.value) {
      loadCardImages(true)
    }
  }
}

// Watch for search query changes
watch(searchQuery, () => {
  cardImages.value = []
  cardOffset.value = 0
  cardHasMore.value = true
  loadCardImages()
})

// Initial load
onMounted(() => {
  loadCardImages()
})

// Sync with parent
watch(() => props.currentImages, (newImages) => {
  galleryImages.value = [...newImages]
}, { deep: true })

// Add selected files to gallery
async function addSelectedToGallery() {
  let selectedFileIds: number[] = []
  
  if (viewMode.value === 'tree') {
    // Tree view now provides numeric file IDs directly from FileBrowserTree
    selectedFileIds = Array.from(treeSelectedFileIds.value)
    console.log('[ImageAssignmentPanel] addSelectedToGallery (tree) - file IDs:', selectedFileIds)
  } else {
    // Card view already has numeric file IDs
    selectedFileIds = Array.from(cardSelectedFiles.value)
  }
  
  if (selectedFileIds.length === 0) {
    console.warn('[ImageAssignmentPanel] addSelectedToGallery - no files selected')
    return
  }
  
  try {
    await $fetch(`/api/galleries/${props.galleryId}/images`, {
      method: 'POST',
      body: { fileIds: selectedFileIds },
    })
    
    // Clear selection
    treeSelectedFileIds.value.clear()
    cardSelectedFiles.value.clear()
    
    // Refresh gallery images
    const updated = await $fetch<Array<{
      id: number; galleryId: number; fileId: number;
      displayOrder: number; caption: string | null;
      addedById: number; addedAt: string;
      fileName?: string; path?: string;
    }>>(`/api/galleries/${props.galleryId}/images`)
    
    galleryImages.value = updated
    emit('update:images', updated)
  } catch (e: any) {
    alert(e.message || e.statusMessage || 'Failed to add images')
  }
}

// (resolveTreeFileIdsFromPaths removed - FileBrowserTree now emits numeric file IDs directly)

// Remove image from gallery
async function removeImage(imageId: number) {
  try {
    await $fetch(`/api/galleries/${props.galleryId}/images/${imageId}`, {
      method: 'DELETE',
    })
    galleryImages.value = galleryImages.value.filter(img => img.id !== imageId)
    emit('update:images', galleryImages.value)
  } catch (e: any) {
    alert(e.message || 'Failed to remove image')
  }
}

// Add a new caption to an image
async function addCaption(imageId: number) {
  const caption = captionEdits.value[imageId]
  if (!caption || caption.trim() === '') return
  
  try {
    const result = await $fetch<Array<{
      captionId: number; galleryImageId: number; caption: string;
      createdById: number; createdAt: string; updatedAt: string;
    }>>(`/api/galleries/${props.galleryId}/images/${imageId}/captions`, {
      method: 'POST',
      body: { caption: caption.trim() },
    })
    
    const img = galleryImages.value.find((img: any) => img.id === imageId)
    if (img) {
      img.captions = (img.captions || []).concat(result)
    }
    captionEdits.value = {}
  } catch (e: any) {
    alert(e.message || 'Failed to add caption')
  }
}

// Delete a caption from an image
async function deleteCaption(imageId: number, captionId: number) {
  try {
    await $fetch(`/api/galleries/${props.galleryId}/images/${imageId}/captions/${captionId}`, {
      method: 'DELETE',
    })
    
    const img = galleryImages.value.find((img: any) => img.id === imageId)
    if (img) {
      img.captions = img.captions.filter((c: any) => c.captionId !== captionId)
    }
  } catch (e: any) {
    alert(e.message || 'Failed to delete caption')
  }
}

// Reorder images
async function moveImage(imageId: number, direction: 'up' | 'down') {
  const index = galleryImages.value.findIndex(img => img.id === imageId)
  if (
    (direction === 'up' && index === 0) ||
    (direction === 'down' && index === galleryImages.value.length - 1)
  ) return
  
  const newImages = [...galleryImages.value]
  const temp = newImages[index]
  const swapIndex = direction === 'up' ? index - 1 : index + 1
  newImages[index] = newImages[swapIndex]
  newImages[swapIndex] = temp
  
  galleryImages.value = newImages
  
  // Update display orders
  const order = newImages.map((img, i) => ({ id: img.id, order: i + 1 }))
  
  try {
    // Note: We'll need to call reorder API or update each image
    // For now, just update locally
    emit('update:images', newImages)
  } catch (e: any) {
    alert(e.message || 'Failed to reorder')
  }
}

// Drag and drop handlers
function onDragStart(fileId: number, event: DragEvent) {
  console.log('[DRAG] dragStart - fileId:', fileId, 'draggedFileId:', draggedFileId.value)
  draggedFileId.value = fileId
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'copy'
    // Required for native HTML5 drag-and-drop to work
    event.dataTransfer.setData('text/plain', String(fileId))
  }
}

function onDragOver(event: DragEvent) {
  console.log('[DRAG] dragOver on drop target')
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy'
  }
}

async function onDrop(event: DragEvent) {
  console.log('[DRAG] drop - draggedFileId:', draggedFileId.value, 'galleryId:', props.galleryId, 'event:', event.type)
  event.preventDefault()
  if (!draggedFileId.value) {
    console.warn('[DRAG] drop - no draggedFileId, aborting')
    return
  }
  
  try {
    // Convert to number - the server expects number/bigint, not string
    const fileIdNum = Number(draggedFileId.value)
    console.log('[DRAG] Sending POST to /api/galleries/', props.galleryId, '/images with fileIds:', [fileIdNum], '(type:', typeof fileIdNum, ')')
    const result = await $fetch(`/api/galleries/${props.galleryId}/images`, {
      method: 'POST',
      body: { fileIds: [fileIdNum] },
    })
    console.log('[DRAG] POST response:', result)
    
    console.log('[DRAG] Fetching updated gallery images...')
    const updated = await $fetch(`/api/galleries/${props.galleryId}/images`)
    console.log('[DRAG] GET response:', updated)
    galleryImages.value = updated
    emit('update:images', updated)
    console.log('[DRAG] Successfully added image to gallery')
  } catch (e: any) {
    console.error('[DRAG] drop error:', e)
    console.error('[DRAG] Error details:', e.message, e.statusCode, e.data)
    alert(e.message || e.statusText || 'Failed to add image: ' + JSON.stringify(e))
  }
  
  draggedFileId.value = null
}

// Preview image
function showPreview(fileId: number, fileName: string) {
  openPreview([{
    fileId,
    filename: fileName,
    previewUrl: getPreviewUrl(fileId, 1080),
  }], fileId)
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <div class="flex flex-col h-[70vh] p-4">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b">
      <div>
        <h3 class="text-lg font-semibold">Assign Images</h3>
        <p class="text-sm text-muted-foreground">
          Add images to "{{ galleryName }}" gallery
        </p>
      </div>
      <Button variant="ghost" size="icon" @click="handleClose">
        <X class="w-4 h-4" />
      </Button>
    </div>

    <!-- View Mode Toggle & Search -->
    <div class="flex items-center gap-2 py-3 border-b">
      <!-- View Mode Toggle -->
      <div class="flex rounded-md border overflow-hidden">
        <button
          class="px-3 py-1.5 text-sm transition-colors"
          :class="viewMode === 'tree' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-accent'"
          @click="viewMode = 'tree'"
        >
          Tree
        </button>
        <button
          class="px-3 py-1.5 text-sm transition-colors border-l"
          :class="viewMode === 'cards' ? 'bg-primary text-primary-foreground' : 'bg-background hover:bg-accent'"
          @click="viewMode = 'cards'"
        >
          Cards
        </button>
      </div>

      <!-- Search -->
      <div class="flex-1 relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          v-model="searchQuery"
          placeholder="Search by filename..."
          class="pl-9"
        />
      </div>

      <!-- Add Button -->
      <Button @click="addSelectedToGallery" :disabled="selectedCount === 0">
        <Plus class="w-4 h-4 mr-2" />
        Add {{ selectedCount > 0 ? `(${selectedCount})` : '' }}
      </Button>
    </div>

    <!-- Main Content Area -->
    <div class="flex flex-1 gap-4 py-3 overflow-hidden">
      <!-- Left Panel: Image Source -->
      <div class="w-96 border rounded-lg flex flex-col overflow-hidden">
        <div class="p-3 border-b bg-muted/30">
          <span class="text-sm font-medium">
            {{ viewMode === 'tree' ? 'File Browser' : 'All Images' }}
          </span>
        </div>
        
        <div class="flex-1 overflow-y-auto p-2">
          <!-- Tree View -->
          <div v-if="viewMode === 'tree'" class="h-full flex flex-col">
            <!-- FileBrowserTree loads its own folders from /api/tags-and-tagging/accessible-folders on mount -->
            <!-- hideTagDescribeButton=true hides "Tag & Describe" button, hideStagedFilter=true hides "Staged" filter -->
            <FileBrowserTree
              :accessible-folders="[]"
              :hide-tag-describe-button="true"
              :hide-staged-filter="true"
              @update:selected-file-ids="handleTreeSelectionChange"
            />
          </div>

          <!-- Card View -->
          <div v-else class="grid grid-cols-4 gap-2">
            <div
              v-for="image in cardImages"
              :key="image.fileId"
              class="relative group aspect-square rounded-md overflow-hidden bg-muted/30 border cursor-pointer"
              :class="cardSelectedFiles.has(image.fileId) ? 'ring-2 ring-primary' : ''"
              draggable="true"
              @click="cardSelectedFiles.has(image.fileId) ? cardSelectedFiles.delete(image.fileId) : cardSelectedFiles.add(image.fileId)"
              @dblclick="showPreview(image.fileId, image.fileName)"
              @dragstart="onDragStart(image.fileId, $event)"
              @dragend="draggedFileId = null"
            >
              <img
                :src="getPreviewUrl(image.fileId, 128)"
                :alt="image.fileName"
                class="w-full h-full object-cover pointer-events-none"
              />
              <!-- Selection checkbox -->
              <div v-if="cardSelectedFiles.has(image.fileId)" class="absolute inset-0 bg-primary/30 flex items-center justify-center">
                <div class="w-5 h-5 bg-primary rounded-full flex items-center justify-center">
                  <svg class="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
              <!-- Tooltip -->
              <div class="absolute bottom-0 left-0 right-0 p-1 bg-black/60 text-white text-[10px] truncate opacity-0 group-hover:opacity-100 transition-opacity">
                {{ image.fileName }}
              </div>
            </div>
          </div>

          <!-- Loading more indicator -->
          <div v-if="cardLoading" class="flex items-center justify-center py-4">
            <Loader2 class="w-5 h-5 animate-spin text-muted-foreground" />
          </div>

          <!-- Empty state -->
          <div v-if="!cardLoading && cardImages.length === 0" class="text-center py-8 text-muted-foreground text-sm">
            <ImageIcon class="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No images found</p>
          </div>
        </div>
      </div>

      <!-- Right Panel: Gallery Images (Drop Target) -->
      <div
        class="flex-1 border rounded-lg flex flex-col overflow-hidden"
        :class="draggedFileId !== null ? 'ring-2 ring-primary ring-dashed' : ''"
        @dragover.prevent="onDragOver"
        @drop.prevent="onDrop"
      >
        <div class="p-3 border-b bg-muted/30 flex items-center justify-between">
          <span class="text-sm font-medium">
            Gallery Images ({{ galleryImages.length }})
          </span>
          <div class="flex gap-2">
            <Button variant="ghost" size="sm">
              <ArrowLeftRight class="w-3 h-3 mr-1" />
              Transfer
            </Button>
          </div>
        </div>

        <!-- Inner drop zone - only handles dragover to allow the outer container's drop handler to fire -->
        <div
          class="flex-1 overflow-y-auto p-3"
          @dragover.prevent="onDragOver"
        >
          <div v-if="galleryImages.length === 0" class="text-center py-12 text-muted-foreground">
            <ImageIcon class="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p class="text-sm">No images in this gallery</p>
            <p class="text-xs mt-1">Drag images here or use the file browser</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="(image, index) in galleryImages"
              :key="image.id"
              class="flex items-center gap-3 p-2 rounded-lg border hover:bg-muted/50 transition-colors group"
              @dragstart.stop="draggedFileId = image.fileId"
              @dragend.stop="draggedFileId = null"
            >
              <!-- Order & Controls -->
              <div class="flex flex-col gap-1">
                <button
                  class="w-5 h-5 flex items-center justify-center hover:bg-muted rounded"
                  :disabled="index === 0"
                  @click="moveImage(image.id, 'up')"
                >
                  <ArrowUp class="w-3 h-3" />
                </button>
                <button
                  class="w-5 h-5 flex items-center justify-center hover:bg-muted rounded"
                  :disabled="index === galleryImages.length - 1"
                  @click="moveImage(image.id, 'down')"
                >
                  <ArrowDown class="w-3 h-3" />
                </button>
              </div>

              <!-- Thumbnail with caption editor button -->
              <div class="relative">
                <img
                  :src="getPreviewUrl(image.fileId, 64)"
                  :alt="image.captions?.[0]?.caption || image.fileName || ''"
                  class="w-12 h-12 rounded object-cover cursor-pointer"
                  @click="showPreview(image.fileId, image.fileName || '')"
                />
                <button
                  class="absolute -top-1 -right-1 p-1 rounded-full bg-primary text-primary-foreground opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                  @click.stop="openCaptionSelector(image)"
                  title="Edit captions"
                >
                  <Pencil class="w-3 h-3" />
                </button>
              </div>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium truncate">{{ image.fileName || `File ${image.fileId}` }}</p>
                
                <!-- Display existing captions -->
                <div v-if="image.captions?.length" class="mt-1 space-y-1">
                  <div v-for="cap in image.captions" :key="cap.captionId" class="flex items-center gap-1">
                    <span class="text-xs text-muted-foreground">{{ cap.caption }}</span>
                    <button
                      class="text-xs text-destructive hover:text-destructive/80"
                      @click="deleteCaption(image.id, cap.captionId)"
                    >
                      ×
                    </button>
                  </div>
                </div>
                
                <!-- Add new caption input -->
                <input
                  v-model="captionEdits[image.id]"
                  placeholder="Add caption..."
                  class="w-full text-xs mt-1 px-2 py-1 rounded border bg-transparent hover:border-input focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
                  @blur="addCaption(image.id)"
                  @keyup.enter="addCaption(image.id)"
                />
              </div>

              <!-- Remove Button -->
              <Button
                variant="ghost"
                size="icon"
                class="opacity-0 group-hover:opacity-100 transition-opacity"
                @click="removeImage(image.id)"
              >
                <X class="w-4 h-4 text-destructive" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between pt-3 border-t">
      <p class="text-xs text-muted-foreground">
        Click to select, double-click to preview, drag to add
      </p>
      <div class="flex gap-2">
        <Button variant="outline" @click="handleClose">Done</Button>
      </div>
    </div>

    <!-- Image Preview Modal -->
    <ImagePreviewModal :state="previewState" :close="closePreview" :navigate="() => {}" />

    <!-- Caption Selector Panel -->
    <CaptionSelectorPanel
      v-if="selectedCaptionImage && showCaptionSelector"
      :gallery-id="galleryId"
      :image-id="selectedCaptionImage.imageId"
      :file-id="selectedCaptionImage.fileId"
      :current-captions="selectedCaptionImage.captions"
      @close="showCaptionSelector = false"
      @update:captions="handleCaptionsUpdate"
    />
  </div>
</template>
