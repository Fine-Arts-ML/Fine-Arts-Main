<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next'

definePageMeta({
  middleware: 'tags-pipeline',
})

onMounted(() => {
  navigateTo('/tags-and-tagging/scan-files')
})
</script>

<template>
  <div class="flex items-center justify-center h-64">
    <Loader2 class="w-8 h-8 animate-spin text-blue-600" />
  </div>
</template>
