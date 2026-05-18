<script setup lang="ts">
import { ChevronRight, CheckCircle } from 'lucide-vue-next'

interface Step {
  id: string
  label: string
  icon: string
}

interface Props {
  steps: Step[]
  currentStep: string
  completeSteps: string[]
}

const props = defineProps<Props>()

function isActive(stepId: string): boolean {
  return stepId === props.currentStep
}

function isStepComplete(stepId: string): boolean {
  return props.completeSteps.includes(stepId)
}

function isLast(index: number): boolean {
  return index === props.steps.length - 1
}
</script>

<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-1 mb-6">
    <div class="flex items-center flex-wrap">
      <NuxtLink
        v-for="(step, index) in steps"
        :key="step.id"
        :to="`/tags-and-tagging/${step.id}`"
        class="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors"
        :class="[
          isActive(step.id)
            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
            : isStepComplete(step.id)
              ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
        ]"
      >
        <span>{{ step.icon }}</span>
        <span class="hidden sm:inline">{{ step.label }}</span>
        <CheckCircle v-if="isStepComplete(step.id) && !isActive(step.id)" class="w-4 h-4" />
      </NuxtLink>
      
      <!-- Step separators -->
      <template v-for="(step, index) in steps" :key="`sep-${step.id}`">
        <ChevronRight
          v-if="!isLast(index)"
          class="w-4 h-4 text-gray-400 mx-1 flex-shrink-0"
        />
      </template>
    </div>
  </div>
</template>
