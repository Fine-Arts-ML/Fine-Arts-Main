<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTheme } from '~/composables/useTheme'
import { useAuth } from '~/composables/useAuth'
import { Sun, Moon, Settings2 } from 'lucide-vue-next'

const { theme, toggleTheme } = useTheme()
const { isAuthenticated } = useAuth()

onMounted(() => {
  // Sync Vue theme ref with actual DOM state (set by inline script in nuxt.config.ts)
  const isDark = document.documentElement.classList.contains('dark')
  if (theme.value !== (isDark ? 'dark' : 'light')) {
    theme.value = isDark ? 'dark' : 'light'
  }
})

definePageMeta({
  layout: 'default',
})

useHead({
  title: 'User Settings - Art Management',
})
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto">
    <!-- Page Header -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-2">
        <Settings2 class="w-6 h-6 text-gray-600 dark:text-gray-400" />
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">User Settings</h1>
      </div>
      <p class="text-gray-600 dark:text-gray-400">Customize your personal preferences</p>
    </div>

    <!-- Appearance Section - Available to all authenticated users -->
    <div v-if="isAuthenticated" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Appearance</h2>
      
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
            <Sun v-if="theme === 'light'" class="w-5 h-5 text-gray-600 dark:text-gray-300" />
            <Moon v-else class="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </div>
          <div>
            <p class="font-medium text-gray-900 dark:text-gray-100">Dark Mode</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ theme === 'light' ? 'Currently using light mode' : 'Currently using dark mode' }}
            </p>
          </div>
        </div>
        
        <button
          @click="toggleTheme"
          class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          :class="theme === 'dark' ? 'bg-blue-600' : 'bg-gray-300'"
          role="switch"
          :aria-checked="theme === 'dark'"
          aria-label="Toggle dark mode"
        >
          <span
            class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm"
            :class="theme === 'dark' ? 'translate-x-6' : 'translate-x-1'"
          />
        </button>
      </div>
    </div>

    <!-- Not authenticated message -->
    <div v-else class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <p class="text-gray-600 dark:text-gray-400">Please log in to access your settings.</p>
    </div>
  </div>
</template>
