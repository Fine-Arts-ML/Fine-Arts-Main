<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  useGalleries,
  type Gallery,
  type GalleryDetail,
  type GalleryImage,
  type GalleryAccessEntry,
} from '~/composables/useGalleries'
import {
  Plus,
  Search,
  Pencil,
  Trash2,
  Users,
  Image as ImageIcon,
  X,
  Eye,
  ChevronRight,
  Loader2,
  FolderOpen,
} from 'lucide-vue-next'
import Button from '~/components/ui/Button.vue'
import Input from '~/components/ui/Input.vue'
import Textarea from '~/components/ui/Textarea.vue'
import Dialog from '~/components/ui/Dialog.vue'
import DialogContent from '~/components/ui/DialogContent.vue'
import DialogHeader from '~/components/ui/DialogHeader.vue'
import DialogTitle from '~/components/ui/DialogTitle.vue'
import DialogDescription from '~/components/ui/DialogDescription.vue'
import DialogFooter from '~/components/ui/DialogFooter.vue'
import ImageAssignmentPanel from '~/components/gallery/ImageAssignmentPanel.vue'
import AccessManagementPanel from '~/components/gallery/AccessManagementPanel.vue'

// Router for navigation
const router = useRouter()

// Use composables
const {
  galleries,
  loading,
  error,
  searchQuery,
  fetchGalleries,
  createGallery,
  updateGallery,
  deleteGallery,
  fetchGallery,
} = useGalleries()

// Selected gallery
const selectedGalleryId = ref<number | null>(null)
const selectedGallery = computed<Gallery | undefined>(() => 
  galleries.value.find((g: Gallery) => g.id === selectedGalleryId.value)
)
const selectedGalleryDetail = computed<GalleryDetail | null>(() => {
  if (!selectedGalleryId.value) return null
  const gallery = galleries.value.find((g: Gallery) => g.id === selectedGalleryId.value)
  return gallery as GalleryDetail | null
})

// New gallery dialog
const showNewGalleryDialog = ref(false)
const newGalleryName = ref('')
const newGalleryDescription = ref('')

// Edit dialog
const showEditDialog = ref(false)
const editingGalleryId = ref<number | null>(null)
const editingName = ref('')
const editingDescription = ref('')

// Image assignment panel
const showImageAssignment = ref(false)
const galleryImagesForPanel = ref<GalleryImage[]>([])

// Access management panel
const showAccessManagement = ref(false)
const galleryAccessForPanel = ref<GalleryAccessEntry[]>([])

// Load galleries on mount
onMounted(async () => {
  await fetchGalleries()
})

// Watch for gallery selection changes
watch(selectedGalleryId, async (newId) => {
  if (newId) {
    await fetchGallery(newId)
  }
})

// Create new gallery
async function handleCreateGallery() {
  if (!newGalleryName.value.trim()) return
  
  try {
    await createGallery(newGalleryName.value, newGalleryDescription.value || undefined)
    showNewGalleryDialog.value = false
    newGalleryName.value = ''
    newGalleryDescription.value = ''
  } catch (e: any) {
    alert(e.message || 'Failed to create gallery')
  }
}

// Start editing
function startEdit(gallery: Gallery) {
  editingGalleryId.value = gallery.id
  editingName.value = gallery.name
  editingDescription.value = gallery.description || ''
  showEditDialog.value = true
}

// Save edit
async function handleSaveEdit() {
  if (!editingGalleryId.value || !editingName.value.trim()) return
  
  try {
    await updateGallery(editingGalleryId.value, {
      name: editingName.value,
      description: editingDescription.value || undefined,
    })
    showEditDialog.value = false
  } catch (e: any) {
    alert(e.message || 'Failed to update gallery')
  }
}

// Delete gallery
async function handleDelete(galleryId: number) {
  if (!confirm('Are you sure you want to delete this gallery? This action cannot be undone.')) return
  
  try {
    await deleteGallery(galleryId)
    if (selectedGalleryId.value === galleryId) {
      selectedGalleryId.value = null
    }
  } catch (e: any) {
    alert(e.message || 'Failed to delete gallery')
  }
}

// Delete image from gallery
async function handleDeleteImage(imageId: number) {
  if (!selectedGalleryId.value) return
  if (!confirm('Remove this image from the gallery?')) return
  
  try {
    await $fetch(`/api/galleries/${selectedGalleryId.value}/images/${imageId}`, {
      method: 'DELETE',
    })
    await refreshGalleryData()
  } catch (e: any) {
    alert(e.message || 'Failed to remove image')
  }
}

// Refresh gallery data
async function refreshGalleryData() {
  if (selectedGalleryId.value) {
    await fetchGallery(selectedGalleryId.value)
  }
}

// Toggle preview mode - navigates to guest gallery viewer
function togglePreview() {
  if (selectedGalleryId.value) {
    router.push(`/gallery/${selectedGalleryId.value}`)
  }
}

// Preview URL helper
function getPreviewUrl(fileId: number, size: number = 32): string {
  return `/api/files/preview-proxy/${fileId}?size=${size}`
}

// Format date
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  
  if (diffHours < 1) return 'Just now'
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return '1 day ago'
  return `${diffDays} days ago`
}

// Image assignment panel handlers
function openImageAssignment() {
  if (selectedGalleryDetail.value) {
    galleryImagesForPanel.value = selectedGalleryDetail.value.images || []
  }
  showImageAssignment.value = true
}

function onUpdateImages(images: GalleryImage[]) {
  galleryImagesForPanel.value = images
  refreshGalleryData()
}

function closeImageAssignment() {
  showImageAssignment.value = false
}

// Access management panel handlers
function openAccessManagement() {
  if (selectedGalleryDetail.value) {
    galleryAccessForPanel.value = selectedGalleryDetail.value.access || []
  }
  showAccessManagement.value = true
}

function onUpdateAccess(access: GalleryAccessEntry[]) {
  galleryAccessForPanel.value = access
  refreshGalleryData()
}

function closeAccessManagement() {
  showAccessManagement.value = false
}
</script>

<template>
  <div class="min-h-screen bg-background">
    <!-- Header -->
    <div class="border-b bg-card/50 backdrop-blur">
      <div class="px-6 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <FolderOpen class="w-6 h-6 text-primary" />
            <div>
              <h1 class="text-2xl font-semibold">Gallery Management</h1>
              <p class="text-sm text-muted-foreground">Create and manage picture galleries</p>
            </div>
          </div>
          <Button @click="showNewGalleryDialog = true">
            <Plus class="w-4 h-4 mr-2" />
            New Gallery
          </Button>
        </div>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="mx-6 mt-4 p-4 bg-destructive/10 border border-destructive rounded-lg flex items-center justify-between">
      <p class="text-destructive">{{ error }}</p>
      <Button variant="ghost" size="sm" @click="error = null">
        <X class="w-4 h-4" />
      </Button>
    </div>

    <!-- Main Content - Split Pane Layout -->
    <div class="flex h-[calc(100vh-100px)]">
      <!-- Left Panel - Gallery List -->
      <div class="w-80 border-r bg-card/30 p-4 overflow-y-auto">
        <div class="relative mb-4">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            v-model="searchQuery"
            placeholder="Search galleries..."
            class="pl-9"
          />
        </div>

        <div v-if="loading" class="flex items-center justify-center py-8">
          <Loader2 class="w-6 h-6 animate-spin text-muted-foreground" />
        </div>

        <div v-else class="space-y-2">
          <div
            v-for="gallery in galleries"
            :key="gallery.id"
            class="p-3 rounded-lg cursor-pointer transition-colors"
            :class="[
              selectedGalleryId === gallery.id 
                ? 'bg-primary/10 border border-primary/30' 
                : 'hover:bg-muted/50 border border-transparent'
            ]"
            @click="selectedGalleryId = gallery.id"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1 min-w-0">
                <h3 class="font-medium truncate">{{ gallery.name }}</h3>
                <p class="text-xs text-muted-foreground mt-1">
                  {{ (gallery as GalleryDetail).images?.length || 0 }} images
                </p>
              </div>
              <ChevronRight class="w-4 h-4 text-muted-foreground flex-shrink-0 ml-2" />
            </div>
          </div>

          <div v-if="!loading && galleries.length === 0" class="text-center py-8 text-muted-foreground">
            <p>No galleries yet</p>
            <p class="text-sm mt-1">Create your first gallery to get started</p>
          </div>
        </div>
      </div>

      <!-- Right Panel - Gallery Detail -->
      <div class="flex-1 p-6 overflow-y-auto">
        <div v-if="!selectedGallery" class="flex items-center justify-center h-full text-muted-foreground">
          <div class="text-center">
            <FolderOpen class="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Select a gallery to view details</p>
          </div>
        </div>

        <div v-else class="max-w-4xl mx-auto">
          <!-- Gallery Header -->
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-semibold">{{ selectedGallery.name }}</h2>
              <p class="text-sm text-muted-foreground mt-1">
                {{ (selectedGallery as GalleryDetail).description || '' }}
              </p>
              <p class="text-xs text-muted-foreground mt-1">
                Last edited {{ formatDate(selectedGallery.updatedAt) }}
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Button variant="outline" @click="togglePreview">
                <Eye class="w-4 h-4 mr-2" />
                Preview as Guest
              </Button>
              <Button variant="outline" @click="startEdit(selectedGallery)">
                <Pencil class="w-4 h-4 mr-2" />
                Edit
              </Button>
              <Button variant="outline" @click="handleDelete(selectedGallery.id)">
                <Trash2 class="w-4 h-4 mr-2" />
                Delete
              </Button>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex flex-wrap gap-3 mb-6">
            <Button @click="openImageAssignment">
              <ImageIcon class="w-4 h-4 mr-2" />
              Assign Images
            </Button>
            <Button @click="openAccessManagement">
              <Users class="w-4 h-4 mr-2" />
              Manage Access
            </Button>
          </div>

          <!-- Gallery Images Grid -->
          <div v-if="selectedGalleryDetail?.images?.length" class="grid grid-cols-4 gap-4">
            <div
              v-for="image in selectedGalleryDetail.images"
              :key="image.id"
              class="relative group aspect-square rounded-lg overflow-hidden bg-muted/30 border"
            >
              <img
                :src="getPreviewUrl(image.fileId, 300)"
                :alt="image.caption || image.fileName || ''"
                class="w-full h-full object-cover"
              />
              <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                <Button size="sm" variant="secondary">
                  <Pencil class="w-3 h-3" />
                </Button>
                <Button size="sm" variant="secondary" @click="handleDeleteImage(image.id)">
                  <Trash2 class="w-3 h-3" />
                </Button>
              </div>
              <div v-if="image.caption" class="absolute bottom-0 left-0 right-0 p-2 bg-black/60 text-white text-xs truncate">
                {{ image.caption }}
              </div>
            </div>
          </div>

          <div v-else class="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
            <ImageIcon class="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No images in this gallery</p>
            <Button variant="outline" class="mt-4" @click="openImageAssignment">
              <Plus class="w-4 h-4 mr-2" />
              Add Images
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- New Gallery Dialog -->
    <Dialog v-model:open="showNewGalleryDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Gallery</DialogTitle>
          <DialogDescription>
            Create a new gallery to organize your pictures.
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-4">
          <div>
            <label class="text-sm font-medium">Gallery Name</label>
            <Input
              v-model="newGalleryName"
              placeholder="e.g., Summer Collection 2024"
              @keyup.enter="handleCreateGallery"
            />
          </div>
          <div>
            <label class="text-sm font-medium">Description (optional)</label>
            <Textarea
              v-model="newGalleryDescription"
              placeholder="Describe this gallery..."
              rows="3"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showNewGalleryDialog = false">Cancel</Button>
          <Button @click="handleCreateGallery" :disabled="!newGalleryName.trim()">
            Create Gallery
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Edit Gallery Dialog -->
    <Dialog v-model:open="showEditDialog">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Gallery</DialogTitle>
          <DialogDescription>
            Update gallery information.
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-4">
          <div>
            <label class="text-sm font-medium">Gallery Name</label>
            <Input
              v-model="editingName"
              placeholder="Gallery name"
            />
          </div>
          <div>
            <label class="text-sm font-medium">Description (optional)</label>
            <Textarea
              v-model="editingDescription"
              placeholder="Describe this gallery..."
              rows="3"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showEditDialog = false">Cancel</Button>
          <Button @click="handleSaveEdit" :disabled="!editingName.trim()">
            Save Changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Image Assignment Panel Dialog -->
    <Dialog v-model:open="showImageAssignment">
      <DialogContent class="max-w-7xl h-[85vh] p-0" :open="showImageAssignment">
        <ImageAssignmentPanel
          v-if="showImageAssignment && selectedGalleryId"
          :gallery-id="selectedGalleryId"
          :gallery-name="selectedGallery?.name || ''"
          :current-images="galleryImagesForPanel"
          @update:images="onUpdateImages"
          @close="closeImageAssignment"
        />
      </DialogContent>
    </Dialog>

    <!-- Access Management Panel Dialog -->
    <Dialog v-model:open="showAccessManagement">
      <DialogContent class="max-w-3xl h-[75vh] p-0" :open="showAccessManagement">
        <AccessManagementPanel
          v-if="showAccessManagement && selectedGalleryId"
          :gallery-id="selectedGalleryId"
          :gallery-name="selectedGallery?.name || ''"
          :current-access="galleryAccessForPanel"
          @update:access="onUpdateAccess"
          @close="closeAccessManagement"
        />
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
/* Global styles for shadcn components */
</style>
