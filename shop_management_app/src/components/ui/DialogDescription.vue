<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '~/lib/constants'

interface Props {
  class?: string
}

const props = defineProps<Props>()

const descClass = computed(() =>
  cn('text-sm text-muted-foreground', props.class)
)
</script>

<template>
  <p :class="descClass">
    <slot />
  </p>
</template>
