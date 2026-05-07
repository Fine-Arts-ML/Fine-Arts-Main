<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ChevronRight, ChevronLeft } from 'lucide-vue-next'
import { useTheme } from '~/composables/useTheme'

const { theme } = useTheme()

onMounted(() => {
  // Sync Vue theme ref with actual DOM state (set by inline script in nuxt.config.ts)
  // This fixes the hydration mismatch where SSR renders 'light' but DOM is 'dark'
  const isDark = document.documentElement.classList.contains('dark')
  if (theme.value !== (isDark ? 'dark' : 'light')) {
    theme.value = isDark ? 'dark' : 'light'
  }
})

const collapsed = ref(false)
const mouseY = ref(0)
const showTrigger = ref(false)
const isHoveringLeftEdge = ref(false)
let mouseMoveTimer: ReturnType<typeof setTimeout> | null = null
let positionUpdateTimer: ReturnType<typeof setTimeout> | null = null

function handleEdgeMouseEnter(e: MouseEvent) {
  // Set initial Y position immediately on entry
  mouseY.value = e.clientY
  isHoveringLeftEdge.value = true
  showTrigger.value = true
}

function handleEdgeMouseMove(e: MouseEvent) {
  // Debounce position updates to avoid Transition re-triggering
  if (positionUpdateTimer) return
  positionUpdateTimer = setTimeout(() => {
    mouseY.value = e.clientY
    positionUpdateTimer = null
  }, 50)
}

function handleEdgeMouseLeave() {
  isHoveringLeftEdge.value = false
  // Delay hiding to allow moving to button
  setTimeout(() => {
    if (!isHoveringLeftEdge.value) {
      showTrigger.value = false
    }
  }, 300)
}

function handleMouseMove(e: MouseEvent) {
  // Debounce position updates on button hover too
  if (positionUpdateTimer) return
  positionUpdateTimer = setTimeout(() => {
    mouseY.value = e.clientY
    positionUpdateTimer = null
  }, 50)
}

function toggleSidebar() {
  collapsed.value = !collapsed.value
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
          <li>
            <NuxtLink
              to="/settings"
              class="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <span class="text-xl">⚙️</span>
              <span class="font-medium">Settings</span>
            </NuxtLink>
          </li>
        </ul>
      </nav>

      <!-- Footer -->
      <div class="p-4 border-t border-gray-200 dark:border-gray-700">
        <p class="text-xs text-gray-500 dark:text-gray-400">Shop Management v0.0.1</p>
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
