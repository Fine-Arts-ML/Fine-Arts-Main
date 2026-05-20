<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '~/lib/constants'

interface Props {
  class?: string
}

const props = defineProps<Props>()

const headerClass = computed(() =>
  cn('flex flex-col space-y-1.5 text-center sm:text-left', props.class)
)
</script>

<template>
  <div :class="headerClass">
    <slot />
  </div>
</template>
