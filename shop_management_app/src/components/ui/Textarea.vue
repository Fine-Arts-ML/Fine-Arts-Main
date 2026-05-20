<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '~/lib/constants'

interface Props {
  modelValue?: string
  placeholder?: string
  disabled?: boolean
  rows?: number
  class?: string
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: '',
  disabled: false,
  rows: 3,
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const textareaClass = computed(() =>
  cn(
    'flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
    props.class
  )
)

function onInput(event: Event) {
  const target = event.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}
</script>

<template>
  <textarea
    :class="textareaClass"
    :placeholder="placeholder"
    :disabled="disabled"
    :rows="rows"
    :value="modelValue"
    @input="onInput"
  />
</template>
