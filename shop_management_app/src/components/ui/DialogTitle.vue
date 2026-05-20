<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '~/lib/constants'

interface Props {
  class?: string
}

const props = defineProps<Props>()

const titleClass = computed(() =>
  cn('text-lg font-semibold leading-none tracking-tight', props.class)
)
</script>

<template>
  <h3 :class="titleClass">
    <slot />
  </h3>
</template>
