<script setup lang="ts">
import { ref, watch, provide } from 'vue'

interface Props {
  modelValue?: boolean
  open?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  open: undefined,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:open': [value: boolean]
}>()

const internalOpen = ref(props.open ?? props.modelValue ?? false)

// Provide open state to child components (DialogContent, etc.)
provide('dialogOpen', internalOpen)

watch(() => props.open ?? props.modelValue, (val) => {
  internalOpen.value = val
})

function setOpen(val: boolean) {
  internalOpen.value = val
  emit('update:modelValue', val)
  emit('update:open', val)
}
</script>

<template>
  <slot :open="internalOpen" :close="() => setOpen(false)" />
</template>
