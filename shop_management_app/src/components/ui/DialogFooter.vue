<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '~/lib/constants'

interface Props {
  class?: string
}

const props = defineProps<Props>()

const footerClass = computed(() =>
  cn(
    'flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2',
    props.class
  )
)
</script>

<template>
  <div :class="footerClass">
    <slot />
  </div>
</template>
