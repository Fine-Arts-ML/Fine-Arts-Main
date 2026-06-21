<script setup lang="ts">
import { useAuth } from '~/composables/useAuth'
import { Settings2, Monitor } from 'lucide-vue-next'

const { isAuthenticated } = useAuth()

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

    <!-- Theme Control Info -->
    <div v-if="isAuthenticated" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-3">
        <Monitor class="w-5 h-5 text-gray-600 dark:text-gray-400" />
        <div>
          <p class="font-medium text-gray-900 dark:text-gray-100">Theme Settings</p>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Change your theme using the theme selector in the sidebar footer. Click your profile icon at the bottom-left to access it.
          </p>
        </div>
      </div>
    </div>

    <!-- Not authenticated message -->
    <div v-else class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <p class="text-gray-600 dark:text-gray-400">Please log in to access your settings.</p>
    </div>
  </div>
</template>
