<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ChevronRight, ChevronLeft, LogOut, User, Settings, ChevronDown, ChevronUp } from 'lucide-vue-next'
import { useTheme } from '~/composables/useTheme'
import { useAuth } from '~/composables/useAuth'

const { theme } = useTheme()
const { user, logout, isAuthenticated, isAdmin } = useAuth()

onMounted(() => {
  // Sync Vue theme ref with actual DOM state (set by inline script in nuxt.config.ts)
  // This fixes the hydration mismatch where SSR renders 'light' but DOM is 'dark'
  const isDark = document.documentElement.classList.contains('dark')
  if (theme.value !== (isDark ? 'dark' : 'light')) {
    theme.value = isDark ? 'dark' : 'light'
  }

  // Close user menu when clicking outside (added after mount when DOM is ready)
  document.addEventListener('mousedown', handleOutsideClick)
})

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
  <div class="min-h-screen flex w-full" :class="theme === 'dark' ? 'dark bg-gray-900' : 'bg-gray-50'">
    <!-- Sidebar -->
    <aside
      class="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300 overflow-hidden"
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
      <nav class="flex-1 p-4 overflow-hidden">
        <ul class="space-y-2">
          <li>
            <NuxtLink
              to="/shops"
              class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
              active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <span class="text-xl">🏪</span>
              <span class="font-medium">Shops & Accounts</span>
            </NuxtLink>
          </li>
          <li>
            <NuxtLink
              to="/files"
              class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
              active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <span class="text-xl">📁</span>
              <span class="font-medium">Files</span>
            </NuxtLink>
          </li>
          <li>
            <NuxtLink
              to="/linked-files"
              class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
              active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <span class="text-xl">🔗</span>
              <span class="font-medium">Linked Files</span>
            </NuxtLink>
          </li>
          <li>
            <NuxtLink
              to="/performance"
              class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
              active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
              inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <span class="text-xl">📊</span>
              <span class="font-medium">Performance</span>
            </NuxtLink>
          </li>
          <!-- Tags & Tagging section (authenticated users only) -->
          <li v-if="isAuthenticated">
            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 px-3 mt-4">
              Tags & Tagging
            </div>
            <ul class="space-y-1 ml-2 border-l border-gray-200 dark:border-gray-700 pl-4">
              <li>
                <NuxtLink
                  to="/tags-and-tagging/scan-files"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">🔍</span>
                  <span class="font-medium">Scan Files</span>
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  to="/tags-and-tagging/tags"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">🏷️</span>
                  <span class="font-medium">Tags & Descriptions Generator</span>
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  to="/tags-and-tagging/review-data"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">✅</span>
                  <span class="font-medium">Review Data</span>
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  to="/tags-and-tagging/sync"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">🔄</span>
                  <span class="font-medium">Tags & Descriptions Manager
                  </span>
                </NuxtLink>
              </li>
            </ul>
          </li>
          <!-- App Settings (admin only) -->
          <li v-if="isAdmin">
            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 px-3 mt-4">
              App Settings
            </div>
            <ul class="space-y-1 ml-2 border-l border-gray-200 dark:border-gray-700 pl-4">
              <li>
                <NuxtLink
                  to="/settings/app/rag"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">🧠</span>
                  <span class="font-medium">RAG Search</span>
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  to="/settings/app/browse"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">📂</span>
                  <span class="font-medium">Browse</span>
                </NuxtLink>
              </li>
              <li>
                <NuxtLink
                  to="/settings/app/user-management"
                  class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors"
                  active-class="bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                  inactive-class="text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <span class="text-lg">👥</span>
                  <span class="font-medium">User Management</span>
                </NuxtLink>
              </li>
            </ul>
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
              <!-- User Settings link -->
              <NuxtLink
                to="/settings/user"
                class="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-t-lg transition-colors"
                @click="showUserMenu = false"
              >
                <Settings class="w-4 h-4" />
                <span>User Settings</span>
              </NuxtLink>
              
              <!-- Logout button -->
              <button
                @click="handleLogout"
                class="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-b-lg transition-colors"
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
    <main class="flex-1 overflow-auto">
     <div :class="theme === 'dark' ? 'dark bg-gray-900' : 'bg-gray-50'">
       <slot />
    </div>
    </main>
  </div>
</template>
