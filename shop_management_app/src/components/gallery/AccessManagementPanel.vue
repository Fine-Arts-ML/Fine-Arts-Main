<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Search, X, UserPlus, UserX, Loader2, Users,
  CheckCircle2, Circle,
} from 'lucide-vue-next'
import { useAuth } from '~/composables/useAuth'
import Button from '../ui/Button.vue'
import Input from '../ui/Input.vue'

const { user: currentUser } = useAuth()

interface Props {
  galleryId: number
  galleryName: string
  currentAccess: Array<{
    galleryId: number
    guestUserId: number
    grantedById: number
    grantedAt: string
    guestName?: string
    guestDisplayname?: string
    grantedByName?: string
  }>
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:access': [access: Props['currentAccess']]
  'close': []
}>()

// Search state
const guestSearchQuery = ref('')
const searchResults = ref<Array<{
  id: number
  nextcloudUid: string
  displayName: string
  email: string
  role: string
  allowedGalleryIds: number[]
}>>([])
const searchLoading = ref(false)
const searchPerformed = ref(false)

// Grant access state
const grantLoading = ref(false)

// Computed
const accessList = ref([...props.currentAccess])
const accessCount = computed(() => accessList.value.length)

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

// Search guests
async function searchGuests() {
  if (!guestSearchQuery.value.trim()) {
    searchResults.value = []
    searchPerformed.value = false
    return
  }
  
  searchLoading.value = true
  try {
    const response = await $fetch(`/api/users?search=${encodeURIComponent(guestSearchQuery.value)}`)
    searchResults.value = response.users || []
    searchPerformed.value = true
  } catch (e: any) {
    console.error('Failed to search users:', e)
  } finally {
    searchLoading.value = false
  }
}

// Grant access
async function grantAccess(userId: number) {
  const user = searchResults.value.find(u => u.id === userId)
  if (!user) return
  
  // Check if already has access
  if (accessList.value.some(a => a.guestUserId === userId)) {
    alert('This user already has access to this gallery')
    return
  }
  
  grantLoading.value = true
  try {
    const currentUserId = currentUser.value?.id
    
    const result = await $fetch(`/api/galleries/${props.galleryId}/access`, {
      method: 'POST',
      body: {
        guestUserId: userId,
        grantedById: currentUserId,
      },
    })
    
    accessList.value.push(result)
    emit('update:access', accessList.value)
    
    // Remove from search results
    searchResults.value = searchResults.value.filter(u => u.id !== userId)
  } catch (e: any) {
    alert(e.message || 'Failed to grant access')
  } finally {
    grantLoading.value = false
  }
}

// Revoke access
async function revokeAccess(userId: number) {
  if (!confirm('Revoke access for this user?')) return
  
  try {
    await $fetch(`/api/galleries/${props.galleryId}/access/${userId}`, {
      method: 'DELETE',
    })
    
    accessList.value = accessList.value.filter(a => a.guestUserId !== userId)
    emit('update:access', accessList.value)
  } catch (e: any) {
    alert(e.message || 'Failed to revoke access')
  }
}

// Get display name for a user
function getDisplayName(entry: typeof accessList.value[0]): string {
  return entry.guestDisplayname || entry.guestName || `User ${entry.guestUserId}`
}

function handleClose() {
  emit('close')
}
</script>

<template>
  <div class="flex flex-col h-[60vh]">
    <!-- Header -->
    <div class="flex items-center justify-between pb-3 border-b">
      <div>
        <h3 class="text-lg font-semibold">Manage Access</h3>
        <p class="text-sm text-muted-foreground">
          Control who can view "{{ galleryName }}"
        </p>
      </div>
      <Button variant="ghost" size="icon" @click="handleClose">
        <X class="w-4 h-4" />
      </Button>
    </div>

    <!-- Grant Access Section -->
    <div class="py-3 border-b">
      <div class="flex items-center gap-2 mb-3">
        <UserPlus class="w-4 h-4 text-muted-foreground" />
        <span class="text-sm font-medium">Grant Access</span>
      </div>
      
      <div class="flex gap-2">
        <div class="flex-1 relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            v-model="guestSearchQuery"
            placeholder="Search by username or display name..."
            class="pl-9"
            @keyup.enter="searchGuests"
          />
        </div>
        <Button @click="searchGuests" :disabled="searchLoading || !guestSearchQuery.trim()">
          <Loader2 v-if="searchLoading" class="w-4 h-4 animate-spin" />
          <Search v-else class="w-4 h-4" />
          <span class="ml-2">Search</span>
        </Button>
      </div>

      <!-- Search Results -->
      <div v-if="searchPerformed && searchResults.length > 0" class="mt-3 border rounded-lg max-h-48 overflow-y-auto">
        <div
          v-for="user in searchResults"
          :key="user.id"
          class="flex items-center justify-between p-2 hover:bg-muted/50 transition-colors border-b last:border-b-0"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <span class="text-sm font-medium text-primary">{{ user.displayName?.[0] || '?' }}</span>
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium truncate">{{ user.displayName || user.nextcloudUid }}</p>
              <p class="text-xs text-muted-foreground truncate">{{ user.nextcloudUid }}</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            @click="grantAccess(user.id)"
            :disabled="grantLoading"
          >
            <UserPlus class="w-3 h-3 mr-1" />
            Grant
          </Button>
        </div>
      </div>

      <div v-if="searchPerformed && searchResults.length === 0 && !searchLoading" class="mt-3 text-center py-4 text-muted-foreground text-sm">
        <p>No users found matching "{{ guestSearchQuery }}"</p>
      </div>
    </div>

    <!-- Current Access List -->
    <div class="flex-1 overflow-y-auto py-3">
      <div class="flex items-center gap-2 mb-3">
        <Users class="w-4 h-4 text-muted-foreground" />
        <span class="text-sm font-medium">Current Access ({{ accessCount }})</span>
      </div>

      <div v-if="accessList.length === 0" class="text-center py-8 text-muted-foreground">
        <Users class="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p class="text-sm">No guests have access to this gallery</p>
        <p class="text-xs mt-1">Search above to grant access</p>
      </div>

      <div v-else class="space-y-2">
        <div
          v-for="entry in accessList"
          :key="entry.guestUserId"
          class="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/30 transition-colors"
        >
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <span class="text-sm font-medium text-primary">{{ getDisplayName(entry)[0] }}</span>
            </div>
            <div>
              <p class="text-sm font-medium">{{ getDisplayName(entry) }}</p>
              <p class="text-xs text-muted-foreground">
                Granted by {{ entry.grantedByName || 'Admin' }}
              </p>
              <p class="text-xs text-muted-foreground">
                {{ formatDate(entry.grantedAt) }}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            class="text-destructive hover:text-destructive"
            @click="revokeAccess(entry.guestUserId)"
          >
            <UserX class="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-between pt-3 border-t">
      <p class="text-xs text-muted-foreground">
        {{ accessCount }} user{{ accessCount !== 1 ? 's' : '' }} have access to this gallery
      </p>
      <Button variant="outline" @click="handleClose">Done</Button>
    </div>
  </div>
</template>
