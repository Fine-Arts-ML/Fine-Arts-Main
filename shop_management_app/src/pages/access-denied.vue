<script setup lang="ts">
import { Lock, ArrowLeft } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
})

useHead({
  title: 'Access Denied - Art Management',
})
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto">
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-12 text-center">
      <Lock class="w-16 h-16 text-red-500 mx-auto mb-4" />
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">Access Denied</h1>
      <p class="text-gray-600 dark:text-gray-400 mb-6">You don't have permission to access this page.</p>
      <NuxtLink
        to="/settings/app/rag"
        class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
      >
        <ArrowLeft class="w-4 h-4" />
        <span>Back to App Settings</span>
      </NuxtLink>
    </div>
  </div>
</template>
