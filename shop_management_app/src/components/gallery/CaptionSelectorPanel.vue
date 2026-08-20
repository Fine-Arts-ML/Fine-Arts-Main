<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { X, Plus, Star, Search } from 'lucide-vue-next'
import Input from '../ui/Input.vue'
import type { GalleryImageCaption } from '~/composables/useGalleries'

interface Props {
  galleryId: number
  imageId: number
  fileId: number
  currentCaptions: GalleryImageCaption[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'update:captions', captions: GalleryImageCaption[]): void
}>()

// State
const searchQuery = ref('')
const newCaptionInput = ref('')
const isLoadingCaptions = ref(false)
const isSaving = ref(false)

// Caption sources from API
interface ShopCaptionSource {
  shopId: number
  shopName: string
  captions: Array<{
    captionId: number
    caption: string
    createdById: number
    createdAt: string
  }>
}

interface GalleryCaptionSource {
  galleryId: number
  galleryName: string
  galleryImageId: number
  captions: Array<{
    captionId: number
    caption: string
    isMain: boolean
    createdById: number
    createdAt: string
  }>
}

const shopCaptions = ref<ShopCaptionSource[]>([])
const galleryCaptions = ref<GalleryCaptionSource[]>([])

// Local caption buffer (not saved until user clicks Save)
interface CaptionAssignment {
  captionId: number
  caption: string
  source: 'shop' | 'gallery'
  sourceName: string
  isMain: boolean
  alreadyLinked: boolean
}

const selectedAssignments = ref<CaptionAssignment[]>([])

// Initialize selectedAssignments from currentCaptions
const currentCaptionIds = ref<Set<number>>(new Set())

function initializeSelections() {
  selectedAssignments.value = []
  currentCaptionIds.value = new Set()

  for (const cap of props.currentCaptions) {
    selectedAssignments.value.push({
      captionId: cap.captionId,
      caption: cap.caption,
      source: cap.source || 'gallery',
      sourceName: 'Current Image',
      isMain: cap.isMain || false,
      alreadyLinked: true,
    })
    currentCaptionIds.value.add(cap.captionId)
  }
}

// Load file-specific captions from API
async function loadFileCaptions() {
  isLoadingCaptions.value = true
  try {
    const result = await $fetch(`/api/files/${props.fileId}/captions`)
    galleryCaptions.value = result.galleries || []
    shopCaptions.value = result.shops || []
    
    // Initialize selections from current captions
    initializeSelections()
  } catch (e: any) {
    console.error('Failed to load captions:', e)
    // Initialize with current captions even if API fails
    initializeSelections()
  } finally {
    isLoadingCaptions.value = false
  }
}

// Computed
const totalAvailableCaptions = computed(() => {
  let count = 0
  for (const shop of shopCaptions.value) {
    count += shop.captions.length
  }
  for (const gallery of galleryCaptions.value) {
    count += gallery.captions.length
  }
  return count
})

const showSearchBox = computed(() => totalAvailableCaptions.value > 10)

const filteredShopCaptions = computed(() => {
  if (!searchQuery.value) return shopCaptions.value
  const query = searchQuery.value.toLowerCase()
  return shopCaptions.value.map(shop => ({
    ...shop,
    captions: shop.captions.filter(c => c.caption.toLowerCase().includes(query)),
  })).filter(shop => shop.captions.length > 0)
})

const filteredGalleryCaptions = computed(() => {
  if (!searchQuery.value) return galleryCaptions.value
  const query = searchQuery.value.toLowerCase()
  return galleryCaptions.value.map(gallery => ({
    ...gallery,
    captions: gallery.captions.filter(c => c.caption.toLowerCase().includes(query)),
  })).filter(gallery => gallery.captions.length > 0)
})

// Get bubble classes based on state
function getBubbleClasses(assignment: CaptionAssignment): string {
  const base = 'px-3 py-1.5 rounded-full text-sm font-medium transition-all border cursor-pointer flex items-center gap-1'
  
  if (assignment.isMain) {
    return `${base} bg-primary text-primary-foreground border-primary`
  }
  
  if (assignment.alreadyLinked) {
    return `${base} bg-purple-50 text-purple-800 border-purple-200 dark:bg-purple-950/30 dark:text-purple-300 dark:border-purple-800`
  }
  
  if (assignment.source === 'shop') {
    return `${base} bg-blue-50 text-blue-800 border-blue-200 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-800`
  }
  
  return `${base} bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800`
}

// Toggle main caption
function toggleMain(captionId: number) {
  for (const assignment of selectedAssignments.value) {
    if (assignment.captionId === captionId) {
      assignment.isMain = !assignment.isMain
    } else {
      assignment.isMain = false
    }
  }
}

// Add caption to selection
function addToSelection(captionId: number, captionText: string, source: 'shop' | 'gallery', sourceName: string) {
  // Check if already selected
  if (selectedAssignments.value.some(a => a.captionId === captionId)) return
  
  selectedAssignments.value.push({
    captionId,
    caption: captionText,
    source,
    sourceName,
    isMain: false,
    alreadyLinked: false,
  })
}

// Remove caption from selection
function removeFromSelection(captionId: number) {
  selectedAssignments.value = selectedAssignments.value.filter(a => a.captionId !== captionId)
}

// Toggle selection (add if not present, remove if present)
function toggleCaptionSelection(captionId: number, captionText: string, source: 'shop' | 'gallery', sourceName: string) {
  const existingIndex = selectedAssignments.value.findIndex(a => a.captionId === captionId)
  if (existingIndex >= 0) {
    selectedAssignments.value.splice(existingIndex, 1)
  } else {
    selectedAssignments.value.push({
      captionId,
      caption: captionText,
      source,
      sourceName,
      isMain: false,
      alreadyLinked: false,
    })
  }
}

// Add new caption
function addNewCaption() {
  const text = newCaptionInput.value.trim()
  if (!text) return
  
  // Generate a temporary captionId (negative to avoid conflicts)
  const tempId = -Date.now()
  
  selectedAssignments.value.push({
    captionId: tempId,
    caption: text,
    source: 'gallery',
    sourceName: 'New',
    isMain: selectedAssignments.value.length === 0, // First caption becomes main
    alreadyLinked: false,
  })
  
  newCaptionInput.value = ''
}

// Save selections
async function saveSelections() {
  isSaving.value = true
  
  try {
    // Filter out temporary captions (newly added with negative IDs)
    const existingCaptions = selectedAssignments.value.filter(a => a.captionId > 0)
    const newCaptions = selectedAssignments.value.filter(a => a.captionId < 0)
    
    // Create new captions first
    let newCaptionIds: number[] = []
    if (newCaptions.length > 0) {
      for (const cap of newCaptions) {
        const result = await $fetch(`/api/galleries/${props.galleryId}/images/${props.imageId}/captions`, {
          method: 'POST',
          body: { caption: cap.caption },
        })
        if (result && result.captionId) {
          newCaptionIds.push(result.captionId)
          // Update the assignment with the real captionId
          cap.captionId = result.captionId
        }
      }
    }
    
    // Combine existing and new caption IDs with their isMain status
    const captionAssignments: Array<{ captionId: number; isMain: boolean }> = []
    
    // Add existing captions
    for (const assignment of existingCaptions) {
      captionAssignments.push({
        captionId: assignment.captionId,
        isMain: assignment.isMain,
      })
    }
    
    // Add new captions
    for (const cap of newCaptions) {
      if (cap.captionId > 0) {
        captionAssignments.push({
          captionId: cap.captionId,
          isMain: cap.isMain,
        })
      }
    }
    
    // Bulk update
    const result = await $fetch(`/api/galleries/${props.galleryId}/images/${props.imageId}/captions/bulk`, {
      method: 'PUT',
      body: { captionAssignments },
    })
    
    emit('update:captions', result)
    emit('close')
  } catch (e: any) {
    console.error('Failed to save captions:', e)
    alert(e.data?.statusMessage || e.statusMessage || 'Failed to save captions')
  } finally {
    isSaving.value = false
  }
}

// Cancel and close
function cancel() {
  emit('close')
}

// Watch for currentCaptions changes
watch(() => props.currentCaptions, () => {
  initializeSelections()
}, { deep: true })

// Load captions on mount
loadFileCaptions()
</script>

<template>
  <Teleport to="body">
    <Transition name="menu">
      <div v-if="true" class="fixed inset-0 z-50 flex justify-end" @click.self="cancel">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/30" @click="cancel"></div>
        
        <!-- Panel -->
        <div class="relative w-full max-w-md bg-white dark:bg-gray-900 shadow-xl border-l border-gray-200 dark:border-gray-700 flex flex-col">
          <!-- Header -->
          <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Caption Editor</h2>
            <button
              @click="cancel"
              class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Content -->
          <div class="flex-1 overflow-y-auto p-4">
            <!-- Loading State -->
            <div v-if="isLoadingCaptions" class="flex items-center justify-center py-12">
              <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>

            <!-- Caption Sources (when loaded) -->
            <div v-else>
              <!-- From Shops Section -->
              <div v-if="filteredShopCaptions.length > 0" class="mb-4">
                <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  From Shops ({{ filteredShopCaptions.reduce((sum, s) => sum + s.captions.length, 0) }})
                </h4>
                <div v-for="shop in filteredShopCaptions" :key="shop.shopId" class="mb-2">
                  <p class="text-xs text-muted-foreground mb-1 ml-1">{{ shop.shopName }}</p>
                  <div class="flex flex-wrap gap-2 ml-2">
                    <button
                      v-for="cap in shop.captions"
                      :key="cap.captionId"
                      class="px-3 py-1.5 rounded-full text-sm font-medium transition-all border cursor-pointer"
                      :class="getBubbleClasses({
                        captionId: cap.captionId,
                        caption: cap.caption,
                        source: 'shop',
                        sourceName: shop.shopName,
                        isMain: false,
                        alreadyLinked: currentCaptionIds.has(cap.captionId),
                      })"
                      @click="addToSelection(cap.captionId, cap.caption, 'shop', shop.shopName)"
                    >
                      {{ cap.caption }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- From Other Galleries Section -->
              <div v-if="filteredGalleryCaptions.length > 0" class="mb-4">
                <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                  From Other Galleries ({{ filteredGalleryCaptions.reduce((sum, g) => sum + g.captions.length, 0) }})
                </h4>
                <div v-for="gallery in filteredGalleryCaptions" :key="gallery.galleryId">
                  <p class="text-xs text-muted-foreground mb-1 ml-1">{{ gallery.galleryName }}</p>
                  <div class="flex flex-wrap gap-2 ml-2">
                    <button
                      v-for="cap in gallery.captions"
                      :key="cap.captionId"
                      class="px-3 py-1.5 rounded-full text-sm font-medium transition-all border cursor-pointer"
                      :class="getBubbleClasses({
                        captionId: cap.captionId,
                        caption: cap.caption,
                        source: 'gallery',
                        sourceName: gallery.galleryName,
                        isMain: cap.isMain,
                        alreadyLinked: currentCaptionIds.has(cap.captionId),
                      })"
                      @click="addToSelection(cap.captionId, cap.caption, 'gallery', gallery.galleryName)"
                    >
                      <span v-if="cap.isMain" class="inline">⭐ </span>
                      {{ cap.caption }}
                    </button>
                  </div>
                </div>
              </div>

              <!-- Empty State -->
              <div v-if="filteredShopCaptions.length === 0 && filteredGalleryCaptions.length === 0" class="text-center py-8 text-muted-foreground">
                <p class="text-sm">No captions found for this file</p>
                <p class="text-xs mt-1">Create a new caption below</p>
              </div>
            </div>

            <!-- Current Image Captions -->
            <div v-if="selectedAssignments.length > 0" class="mb-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Current Image Captions ({{ selectedAssignments.filter(a => a.alreadyLinked).length }})
              </h4>
              <div class="space-y-2">
                <div
                  v-for="assignment in selectedAssignments"
                  :key="assignment.captionId"
                  class="flex items-center gap-2 p-2 rounded-lg border"
                  :class="assignment.alreadyLinked 
                    ? 'bg-purple-50 border-purple-200 dark:bg-purple-950/30 dark:border-purple-800'
                    : 'bg-muted/50 border-border'"
                >
                  <!-- Main toggle -->
                  <button
                    @click="toggleMain(assignment.captionId)"
                    class="p-1 rounded hover:bg-muted/50 transition-colors"
                    :title="assignment.isMain ? 'Remove main caption' : 'Set as main caption'"
                  >
                    <Star
                      class="w-4 h-4"
                      :class="assignment.isMain ? 'fill-yellow-400 text-yellow-400' : 'text-muted-foreground'"
                    />
                  </button>
                  
                  <!-- Caption text -->
                  <span class="flex-1 text-sm">{{ assignment.caption }}</span>
                  
                  <!-- Source badge -->
                  <span class="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                    {{ assignment.source }}
                  </span>
                  
                  <!-- Remove button -->
                  <button
                    @click="removeFromSelection(assignment.captionId)"
                    class="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    title="Remove caption"
                  >
                    <X class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>

            <!-- New Caption Input -->
            <div class="mb-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                New Caption
              </h4>
              <div class="flex gap-2">
                <Input
                  v-model="newCaptionInput"
                  placeholder="Type new caption..."
                  @keyup.enter="addNewCaption"
                />
                <Button
                  variant="outline"
                  size="sm"
                  @click="addNewCaption"
                  :disabled="!newCaptionInput.trim()"
                >
                  <Plus class="w-4 h-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="p-4 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            <Button variant="outline" @click="cancel" :disabled="isSaving">
              Cancel
            </Button>
            <Button @click="saveSelections" :disabled="isSaving">
              <span v-if="isSaving" class="mr-2 animate-spin">⏳</span>
              {{ isSaving ? 'Saving...' : 'Save & Close' }}
            </Button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.3s ease;
}

.menu-enter-active div.relative,
.menu-leave-active div.relative {
  transition: transform 0.2s ease;
}

.menu-enter-from,
.menu-leave-to {
  opacity: 0;
}

.menu-enter-from div.relative,
.menu-leave-to div.relative {
  transform: translateX(100%);
}
</style>
