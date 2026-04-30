<script setup lang="ts">
import { X, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import type { PreviewImage } from '~/composables/useImagePreview'

const props = defineProps<{
  state: {
    isOpen: boolean
    currentImage: PreviewImage | null
    images: PreviewImage[]
  }
  close: () => void
  navigate: (direction: 'prev' | 'next') => void
}>()

function handleOverlayClick(event: MouseEvent) {
  if ((event.target as HTMLElement).classList.contains('overlay')) {
    props.close()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="preview">
      <div v-if="state.isOpen" class="fixed inset-0 z-[100] flex items-center justify-center overlay" @click="handleOverlayClick">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/90"></div>

        <!-- Close Button -->
        <button
          class="absolute top-4 right-4 z-[101] p-2 text-white/70 hover:text-white bg-black/50 rounded-full transition-colors"
          @click.stop="close"
        >
          <X class="w-6 h-6" />
        </button>

        <!-- Navigation Arrows (only in gallery mode) -->
        <button
          v-if="state.images.length > 1"
          class="absolute left-4 z-[101] p-2 text-white/70 hover:text-white bg-black/50 rounded-full transition-colors"
          @click.stop="navigate('prev')"
        >
          <ChevronLeft class="w-6 h-6" />
        </button>
        <button
          v-if="state.images.length > 1"
          class="absolute right-4 z-[101] p-2 text-white/70 hover:text-white bg-black/50 rounded-full transition-colors"
          @click.stop="navigate('next')"
        >
          <ChevronRight class="w-6 h-6" />
        </button>

        <!-- Image Container -->
        <div class="relative z-[101] flex flex-col items-center">
          <img
            v-if="state.currentImage"
            :src="state.currentImage.previewUrl"
            :alt="state.currentImage.filename"
            class="max-w-[90vw] max-h-[85vh] object-contain rounded"
            style="min-width: 1080px; min-height: 1080px;"
            @click.stop
          />
          <!-- Filename -->
          <div class="mt-4 px-4 py-2 bg-black/50 rounded-lg">
            <p class="text-white text-sm truncate max-w-[600px]">{{ state.currentImage?.filename }}</p>
          </div>
          <!-- Counter (gallery mode) -->
          <p v-if="state.images.length > 1" class="text-white/70 text-xs mt-2">
            {{ state.images.indexOf(state.currentImage!) + 1 }} / {{ state.images.length }}
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.preview-enter-active,
.preview-leave-active {
  transition: opacity 0.2s ease;
}

.preview-enter-from,
.preview-leave-to {
  opacity: 0;
}
</style>
