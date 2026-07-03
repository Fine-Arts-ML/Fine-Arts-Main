<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import {
  ChevronRight, ChevronLeft, LogOut, User, Settings, ChevronDown, ChevronUp,
  Sun, Moon, Monitor,
  // Sidebar section/menu icons (replacing emojis)
  Building2, Store, Folder, Link, BarChart3,
  GalleryVertical, ClipboardList, Tag, ScanLine,
  PenTool, CheckSquare, RotateCw, Brain, FolderOpen, Users,
  // Guest sidebar icons
  Loader2, EyeOff,
} from 'lucide-vue-next'
import { useTheme } from '~/composables/useTheme'
import { useAuth } from '~/composables/useAuth'
import { useRoute } from 'vue-router'

const { theme, applyTheme, getResolvedTheme } = useTheme()
const { user, logout, isAuthenticated, isAdmin, isGuest } = useAuth()
const route = useRoute()

// Guest gallery data (only loaded when user is guest)
const guestGalleries = ref<Array<{ id: number; name: string; imageCount?: number }>>([])
const guestGalleriesLoading = ref(false)

async function fetchGuestGalleries() {
  if (!isGuest.value) return
  guestGalleriesLoading.value = true
  try {
    const galleries = await $fetch<any[]>('/api/galleries/my')
    guestGalleries.value = galleries.map((g: any) => ({
      id: g.id,
      name: g.name,
      imageCount: g.imageCount,
    }))
  } catch (e) {
    console.error('[sidebar] Failed to fetch guest galleries:', e)
  } finally {
    guestGalleriesLoading.value = false
  }
}

// Watch for guest role changes and fetch galleries
watch(isGuest, (newIsGuest) => {
  if (newIsGuest) {
    fetchGuestGalleries()
  }
})

// Section expand/collapse state — all collapsed by default
const sectionState = ref<Record<string, boolean>>({
  shopsFiles: false,
  galleries: false,
  tags: false,
  settings: false,
})

function toggleSection(section: string) {
  sectionState.value[section] = !sectionState.value[section]
  try {
    localStorage.setItem('sidebarSections', JSON.stringify(sectionState.value))
  } catch (e) { /* ignore localStorage errors */ }
}

function autoExpandSection() {
  const path = route.path
  if (path.startsWith('/shops') || path.startsWith('/files') || path.startsWith('/linked-files') || path.startsWith('/performance')) sectionState.value.shopsFiles = true
  if (path.startsWith('/tags-and-tagging')) sectionState.value.tags = true
  if (path.startsWith('/settings/app')) sectionState.value.settings = true
  if (path.startsWith('/gallery') || path.startsWith('/galleries')) sectionState.value.galleries = true
}

onMounted(() => {
  // Theme state is already synced from localStorage by useTheme() composable
  // Close user menu when clicking outside (added after mount when DOM is ready)
  document.addEventListener('mousedown', handleOutsideClick)

  // Load saved section state from localStorage
  try {
    const saved = localStorage.getItem('sidebarSections')
    if (saved) {
      const parsed = JSON.parse(saved)
      // Merge with defaults, ensuring shopsFiles is initialized
      sectionState.value = {
        shopsFiles: false,
        galleries: parsed.galleries ?? false,
        tags: parsed.tags ?? false,
        settings: parsed.settings ?? false,
      }
    }
  } catch (e) { /* ignore invalid data */ }

  // Auto-expand section based on current route
  autoExpandSection()

  // Fetch guest galleries if user is a guest (for guests already logged in on mount)
  if (isGuest.value) {
    fetchGuestGalleries()
  }
})

// Watch for route changes and auto-expand relevant section
watch(() => route.path, autoExpandSection)

onUnmounted(() => {
  document.removeEventListener('mousedown', handleOutsideClick)
})

const collapsed = ref(false)
const mouseY = ref(0)
const showTrigger = ref(false)
const isHoveringLeftEdge = ref(false)
const showUserMenu = ref(false)
let mouseMoveTimer: ReturnType<typeof setTimeout> | null = null
let positionUpdateTimer: ReturnType<typeof setTimeout> | null = null

// Theme mode selector
function setThemeMode(mode: 'light' | 'dark' | 'auto') {
  applyTheme(mode)
  theme.value = mode
}

const resolvedTheme = computed(() => getResolvedTheme())

function handleOutsideClick(e: MouseEvent) {
  const el = document.querySelector('[data-user-menu]')
  if (el && !el.contains(e.target as Node)) {
    showUserMenu.value = false
  }
}

function handleEdgeMouseEnter(e: MouseEvent) {
  mouseY.value = e.clientY
  isHoveringLeftEdge.value = true
  showTrigger.value = true
}

function handleEdgeMouseMove(e: MouseEvent) {
  if (positionUpdateTimer) return
  positionUpdateTimer = setTimeout(() => {
    mouseY.value = e.clientY
    positionUpdateTimer = null
  }, 50)
}

function handleEdgeMouseLeave() {
  isHoveringLeftEdge.value = false
  setTimeout(() => {
    if (!isHoveringLeftEdge.value) {
      showTrigger.value = false
    }
  }, 300)
}

function handleMouseMove(e: MouseEvent) {
  if (positionUpdateTimer) return
  positionUpdateTimer = setTimeout(() => {
    mouseY.value = e.clientY
    positionUpdateTimer = null
  }, 50)
}

function toggleSidebar() {
  collapsed.value = !collapsed.value
}

async function handleLogout() {
  await logout()
  showUserMenu.value = false
}
</script>

<template>
  <div class="min-h-screen flex w-full bg-gray-50 dark:bg-gray-900">
    <!-- Sidebar -->
    <aside
      class="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300 overflow-x-hidden sticky top-0 h-dvh"
      :class="collapsed ? 'w-0' : 'w-64'"
      :style="collapsed ? 'min-width: 0' : 'min-width: 16rem'"
    >
      <!-- Logo / Title with Collapse Button -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h1 class="text-xl font-bold text-gray-900 dark:text-gray-100">Art Management</h1>
        <button
          @click="toggleSidebar"
          class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-300 transition-colors flex-shrink-0"
          title="Collapse sidebar"
        >
          <ChevronLeft class="w-4 h-4" />
        </button>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 overflow-y-auto">
        <ul class="space-y-2">
          <!-- Shops & Files section (hidden for guests) -->
          <li v-if="!isGuest">
            <button
              @click="toggleSection('shopsFiles')"
              class="w-full flex items-center justify-between text-sm font-bold text-gray-800 dark:text-gray-200 uppercase tracking-widest px-3 py-3 mt-2 border-b border-gray-300 dark:border-gray-600"
            >
              <span class="flex items-center gap-2">
                <Building2 class="w-5 h-5" />
                Shops & Files
              </span>
              <component :is="sectionState.shopsFiles ? ChevronUp : ChevronDown" class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform duration-200" />
            </button>
            <transition
              enter-active-class="transition-all duration-200 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-[400px] opacity-100"
              leave-from-class="max-h-[400px] opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <div
                v-show="sectionState.shopsFiles"
                class="mt-1 ml-1 space-y-0.5 overflow-hidden"
              >
                <li>
                  <NuxtLink
                    to="/shops"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <Store class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Shops & Accounts</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/files"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <Folder class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Files</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/linked-files"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <Link class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Linked Files</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/performance"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <BarChart3 class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Performance</span>
                  </NuxtLink>
                </li>
              </div>
            </transition>
          </li>
          <!-- Galleries section (authenticated users only) -->
          <li v-if="isAuthenticated">
            <!-- For guests: show individual gallery links -->
            <template v-if="isGuest">
              <li class="px-3 py-2 mt-1">
                <div class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest mb-2">My Galleries</div>
              </li>
              <li v-if="guestGalleriesLoading">
                <div class="flex items-center gap-3 px-3 py-2 text-gray-600 dark:text-gray-400">
                  <Loader2 class="w-4 h-4 animate-spin" />
                  <span class="text-sm font-normal">Loading...</span>
                </div>
              </li>
              <li v-else-if="guestGalleries.length === 0">
                <div class="flex items-center gap-3 px-3 py-2 text-gray-500 dark:text-gray-400">
                  <EyeOff class="w-4 h-4 opacity-80" />
                  <span class="text-sm font-normal">No galleries available</span>
                </div>
              </li>
              <li v-else>
                <NuxtLink
                  v-for="gallery in guestGalleries"
                  :key="gallery.id"
                  :to="`/gallery/${gallery.id}`"
                  class="flex items-center justify-between gap-2 px-3 py-2 rounded-md transition-colors"
                  active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                  inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <div class="flex items-center gap-3 min-w-0">
                    <ClipboardList class="w-4 h-4 opacity-80 flex-shrink-0" />
                    <span class="text-sm font-normal truncate">{{ gallery.name }}</span>
                  </div>
                  <span v-if="gallery.imageCount" class="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">
                    {{ gallery.imageCount }}
                  </span>
                </NuxtLink>
              </li>
            </template>
            <!-- For non-guests: show original galleries section -->
            <template v-else>
              <button
                @click="toggleSection('galleries')"
                class="w-full flex items-center justify-between text-sm font-bold text-gray-800 dark:text-gray-200 uppercase tracking-widest px-3 py-3 mt-2 border-b border-gray-300 dark:border-gray-600 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
              >
                <span class="flex items-center gap-2">
                  <GalleryVertical class="w-5 h-5" />
                  Galleries
                </span>
                <component :is="sectionState.galleries ? ChevronUp : ChevronDown" class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform duration-200" />
              </button>
              <transition
                enter-active-class="transition-all duration-200 ease-out"
                enter-from-class="max-h-0 opacity-0"
                enter-to-class="max-h-[300px] opacity-100"
                leave-from-class="max-h-[300px] opacity-100"
                leave-to-class="max-h-0 opacity-0"
              >
                <div
                  v-show="sectionState.galleries"
                  class="mt-1 ml-1 space-y-0.5 overflow-hidden"
                >
                  <li>
                    <NuxtLink
                      to="/galleries"
                      class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                      active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                      inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <ClipboardList class="w-4 h-4 opacity-80" />
                      <span class="text-sm font-normal">Gallery Management</span>
                    </NuxtLink>
                  </li>
                </div>
              </transition>
            </template>
          </li>
          <!-- Tags & Descriptions section (hidden for guests) -->
          <li v-if="isAuthenticated && !isGuest">
            <button
              @click="toggleSection('tags')"
              class="w-full flex items-center justify-between text-sm font-bold text-gray-800 dark:text-gray-200 uppercase tracking-widest px-3 py-3 mt-2 border-b border-gray-300 dark:border-gray-600 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              <span class="flex items-center gap-2 text-left">
                <Tag class="w-5 h-5" />
                <span>Tags & Descriptions</span>
              </span>
              <component :is="sectionState.tags ? ChevronUp : ChevronDown" class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform duration-200" />
            </button>
            <transition
              enter-active-class="transition-all duration-200 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-[500px] opacity-100"
              leave-from-class="max-h-[500px] opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <div
                v-show="sectionState.tags"
                class="mt-1 ml-1 space-y-0.5 overflow-hidden"
              >
                <li>
                  <NuxtLink
                    to="/tags-and-tagging/scan-files"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <ScanLine class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Scan Files</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/tags-and-tagging/tags"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <PenTool class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Tags & Descriptions Generator</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/tags-and-tagging/review-data"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <CheckSquare class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Review Data</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/tags-and-tagging/sync"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <RotateCw class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Tags & Descriptions Manager</span>
                  </NuxtLink>
                </li>
              </div>
            </transition>
          </li>
          <!-- App Settings (admin only) -->
          <li v-if="isAdmin">
            <button
              @click="toggleSection('settings')"
              class="w-full flex items-center justify-between text-sm font-bold text-gray-800 dark:text-gray-200 uppercase tracking-widest px-3 py-3 mt-2 border-b border-gray-300 dark:border-gray-600 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            >
              <span class="flex items-center gap-2">
                <Settings class="w-5 h-5" />
                App Settings
              </span>
              <component :is="sectionState.settings ? ChevronUp : ChevronDown" class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform duration-200" />
            </button>
            <transition
              enter-active-class="transition-all duration-200 ease-out"
              enter-from-class="max-h-0 opacity-0"
              enter-to-class="max-h-[400px] opacity-100"
              leave-from-class="max-h-[400px] opacity-100"
              leave-to-class="max-h-0 opacity-0"
            >
              <div
                v-show="sectionState.settings"
                class="mt-1 ml-1 space-y-0.5 overflow-hidden"
              >
                <li>
                  <NuxtLink
                    to="/settings/app/rag"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <Brain class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">RAG Search</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/settings/app/browse"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <FolderOpen class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">Browse</span>
                  </NuxtLink>
                </li>
                <li>
                  <NuxtLink
                    to="/settings/app/user-management"
                    class="flex items-center gap-3 px-3 py-2 rounded-md transition-colors"
                    active-class="bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
                    inactive-class="text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <Users class="w-4 h-4 opacity-80" />
                    <span class="text-sm font-normal">User Management</span>
                  </NuxtLink>
                </li>
              </div>
            </transition>
          </li>
        </ul>
      </nav>

      <!-- Footer / User Section -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700">
        <!-- User info and logout dropdown -->
        <div v-if="isAuthenticated && user" class="relative" data-user-menu>
          <!-- Clickable user button -->
          <button
            @click="showUserMenu = !showUserMenu"
            class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left"
          >
            <div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center flex-shrink-0">
              <User class="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{{ user.username }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400 capitalize">{{ user.role }}</p>
            </div>
            <component :is="showUserMenu ? ChevronUp : ChevronDown" class="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />
          </button>
          
          <!-- Dropdown menu -->
          <transition
            enter-active-class="transition duration-100 ease-out"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
            leave-active-class="transition duration-75 ease-in"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
          >
            <div
              v-show="showUserMenu"
              class="absolute bottom-full left-0 right-0 mb-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50"
            >
              <!-- Theme Mode Selection -->
              <div class="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
                <p class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Theme</p>
                <div class="flex gap-1">
                  <button
                    @click="setThemeMode('light')"
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium transition-colors"
                    :class="theme === 'light'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'"
                    title="Light mode"
                    aria-label="Switch to light mode"
                  >
                    <Sun class="w-4 h-4" />
                    <span>Light</span>
                  </button>
                  <button
                    @click="setThemeMode('dark')"
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium transition-colors"
                    :class="theme === 'dark'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'"
                    title="Dark mode"
                    aria-label="Switch to dark mode"
                  >
                    <Moon class="w-4 h-4" />
                    <span>Dark</span>
                  </button>
                  <button
                    @click="setThemeMode('auto')"
                    class="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded text-xs font-medium transition-colors"
                    :class="theme === 'auto'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600 border border-transparent'"
                    title="Automatic (follow system)"
                    aria-label="Switch to automatic theme mode"
                  >
                    <Monitor class="w-4 h-4" />
                    <span>Auto</span>
                  </button>
                </div>
              </div>
              
              <!-- User Settings link (hidden for guests) -->
              <NuxtLink
                v-if="!isGuest"
                to="/settings/user"
                class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                @click="showUserMenu = false"
              >
                <Settings class="w-4 h-4" />
                <span>User Settings</span>
              </NuxtLink>
              
              <!-- Logout button -->
              <button
                @click="handleLogout"
                class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <LogOut class="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          </transition>
        </div>
        <div v-else>
          <NuxtLink
            to="/login"
            class="w-full flex items-center justify-center gap-2 px-3 py-2 text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <User class="w-4 h-4" />
            <span>Login</span>
          </NuxtLink>
        </div>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">Shop Management v0.0.1</p>
      </div>
    </aside>

    <!-- Left Edge Hover Zone (always present, triggers expand button) -->
    <div
      class="fixed left-0 top-0 h-full w-10 z-30"
      :style="collapsed ? {} : { display: 'none' }"
      @mouseenter="handleEdgeMouseEnter"
      @mousemove="handleEdgeMouseMove"
      @mouseleave="handleEdgeMouseLeave"
    />

    <!-- Expand Button (follows cursor Y position, flush left edge, only when collapsed) -->
    <div
      v-show="collapsed && showTrigger"
      :style="{ top: mouseY + 'px' }"
      class="fixed left-0 z-50 transition-opacity duration-150"
      :class="showTrigger ? 'opacity-100' : 'opacity-0'"
    >
      <button
        class="p-1.5 rounded-r-md bg-white dark:bg-gray-800 border border-r-0 border-gray-200 dark:border-gray-700 shadow-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        @click.stop="toggleSidebar"
        @mouseenter="handleMouseMove"
        @mousemove="handleMouseMove"
        @mouseleave="showTrigger = false"
        title="Open sidebar"
      >
        <ChevronRight class="w-4 h-4 text-gray-600 dark:text-gray-300" />
      </button>
    </div>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto">
     <div class="bg-gray-50 dark:bg-gray-900">
       <slot />
     </div>
     </main>
  </div>
</template>
