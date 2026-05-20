<script setup lang="ts">
import { computed, onMounted, onUnmounted, inject, type Ref } from 'vue'
import { cn } from '~/lib/utils'

interface Props {
  class?: string
  open?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'close': []
  'update:open': [value: boolean]
}>()

// Inject open state from parent Dialog component via provide/inject
const dialogOpen = inject<Ref<boolean | undefined>>('dialogOpen', undefined as unknown as Ref<boolean | undefined>)

// Use injected open state if available, otherwise fall back to prop
const isOpen = computed(() => dialogOpen?.value ?? props.open ?? false)

const dialogClass = computed(() =>
  cn(
    'fixed left-1/2 top-1/2 z-50 flex flex-col w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg duration-200 sm:rounded-lg',
    props.class
  )
)

function onOverlayClick(event: MouseEvent) {
  if ((event.target as HTMLElement).classList.contains('dialog-overlay')) {
    emit('close')
    emit('update:open', false)
  }
}

onMounted(() => {
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<template>
  <div v-if="isOpen" class="dialog-overlay fixed inset-0 z-40 bg-black/80" @click="onOverlayClick">
    <div :class="dialogClass">
      <slot />
    </div>
  </div>
</template>
