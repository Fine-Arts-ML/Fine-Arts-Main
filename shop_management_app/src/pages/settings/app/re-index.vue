<script setup lang="ts">
import { onMounted } from 'vue'
import { Loader2 } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'admin',
})

useHead({
  title: 'Browse Folders - Art Management',
})

// Redirect to the new Browse page
onMounted(() => {
  navigateTo('/settings/app/browse')
})
</script>

<template>
  <div class="flex items-center justify-center h-64">
    <Loader2 class="w-8 h-8 animate-spin text-blue-600" />
  </div>
</template>
