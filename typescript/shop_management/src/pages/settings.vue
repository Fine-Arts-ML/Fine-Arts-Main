<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTheme } from '~/composables/useTheme'
import { useRAGSettings } from '~/composables/useRAGSettings'
import { Sun, Moon, Cpu, HardDrive, Zap, Loader2, AlertCircle, RefreshCw, Download, Database } from 'lucide-vue-next'

const { theme, toggleTheme } = useTheme()
const {
  selectedModel,
  maxCachedModels,
  cachedModelsCount,
  models,
  currentModelInfo,
  isLoading,
  error,
  loadSettings,
  switchModel,
  updateCacheConfig,
  evictUnusedModels,
  isInCache,
  downloadModel,
  rebuildIndex
} = useRAGSettings()

// Confirmation state for destructive actions
const showReindexConfirm = ref(false)
const showDownloadConfirm = ref(false)
const downloadingModel = ref<string | null>(null)
const reindexing = ref(false)

/**
 * Handle model download with confirmation.
 */
async function handleDownloadModel() {
  downloadingModel.value = 'qwen3-0.6b'
  try {
    await downloadModel('qwen3-0.6b', 'https://huggingface.co/Qwen/Qwen3-Embedding-0.6B')
    showDownloadConfirm.value = false
  } catch {
    // Error is handled by the composable
  } finally {
    downloadingModel.value = null
  }
}

/**
 * Handle TF-IDF index rebuild with confirmation.
 */
async function handleRebuildIndex() {
  reindexing.value = true
  try {
    await rebuildIndex()
    showReindexConfirm.value = false
  } catch {
    // Error is handled by the composable
  } finally {
    reindexing.value = false
  }
}

onMounted(() => {
  // Sync Vue theme ref with actual DOM state (set by inline script in nuxt.config.ts)
  const isDark = document.documentElement.classList.contains('dark')
  if (theme.value !== (isDark ? 'dark' : 'light')) {
    theme.value = isDark ? 'dark' : 'light'
  }
  
  // Load RAG settings
  loadSettings()
})

definePageMeta({
  layout: 'default',
})

useHead({
  title: 'Settings - Art Management',
})
</script>

<template>
  <div class="p-6 max-w-2xl mx-auto">
    <!-- Page Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
      <p class="text-gray-600 dark:text-gray-400 mt-1">Customize your experience</p>
    </div>

    <!-- Appearance Section -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Appearance</h2>
      
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
            <Sun v-if="theme === 'light'" class="w-5 h-5 text-gray-600 dark:text-gray-300" />
            <Moon v-else class="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </div>
          <div>
            <p class="font-medium text-gray-900 dark:text-gray-100">Dark Mode</p>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ theme === 'light' ? 'Currently using light mode' : 'Currently using dark mode' }}
            </p>
          </div>
        </div>
        
        <button
          @click="toggleTheme"
          class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800"
          :class="theme === 'dark' ? 'bg-blue-600' : 'bg-gray-300'"
          role="switch"
          :aria-checked="theme === 'dark'"
          aria-label="Toggle dark mode"
        >
          <span
            class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm"
            :class="theme === 'dark' ? 'translate-x-6' : 'translate-x-1'"
          />
        </button>
      </div>
    </div>

    <!-- RAG Search Section -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">RAG Search</h2>
        <button
          @click="loadSettings"
          :disabled="isLoading"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
          title="Refresh settings"
        >
          <RefreshCw :class="{ 'animate-spin': isLoading }" class="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Configure semantic search settings. Models are loaded on demand from the shared volume.
      </p>

      <!-- Error Message -->
      <div
        v-if="error"
        class="mb-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-sm text-red-700 dark:text-red-300"
      >
        <AlertCircle class="w-4 h-4 flex-shrink-0" />
        {{ error }}
      </div>

      <!-- Max Cached Models -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
          Maximum Cached Models
        </label>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
          Number of models to keep loaded in RAM simultaneously. Higher = faster switching but more RAM usage.
        </p>
        <div class="flex items-center gap-3">
          <input
            type="range"
            min="1"
            max="3"
            v-model.number="maxCachedModels"
            class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
            @change="updateCacheConfig(maxCachedModels)"
          />
          <div class="flex items-center gap-2 min-w-[120px] justify-end">
            <button
              class="w-8 h-8 flex items-center justify-center rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              :disabled="maxCachedModels <= 1 || isLoading"
              @click="updateCacheConfig(maxCachedModels - 1)"
            >
              −
            </button>
            <span class="font-mono text-lg font-bold w-6 text-center text-gray-900 dark:text-gray-100">{{ maxCachedModels }}</span>
            <button
              class="w-8 h-8 flex items-center justify-center rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50"
              :disabled="maxCachedModels >= 3 || isLoading"
              @click="updateCacheConfig(maxCachedModels + 1)"
            >
              +
            </button>
          </div>
        </div>
        <!-- RAM Estimate -->
        <div class="mt-2 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
          <HardDrive class="w-3 h-3" />
          Estimated RAM: ~{{ maxCachedModels * 2 }}GB (based on ~2GB per model)
        </div>
      </div>

      <!-- Available Models -->
      <div>
        <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Available Models</h3>
        <p class="text-xs text-gray-500 dark:text-gray-400 mb-3">
          Models are discovered from the shared volume. Add model folders to make them available.
        </p>
        
        <!-- Loading State -->
        <div v-if="isLoading && models.length === 0" class="flex items-center justify-center py-8">
          <Loader2 class="w-6 h-6 animate-spin text-gray-400" />
        </div>

        <!-- Model Selection -->
        <div v-else class="space-y-3">
          <label
            v-for="model in models"
            :key="model.id"
            class="flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all"
            :class="selectedModel === model.id
              ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/50 ring-1 ring-blue-500'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'"
            @click="switchModel(model.id)"
          >
            <input
              type="radio"
              :value="model.id"
              v-model="selectedModel"
              class="sr-only"
              @change="switchModel(model.id)"
              :disabled="isLoading"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-gray-900 dark:text-gray-100">{{ model.name }}</span>
                <span v-if="model.id === selectedModel" class="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">Current</span>
                <span v-if="isInCache(model.id)" class="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs rounded-full flex items-center gap-1">
                  <Cpu class="w-3 h-3" />
                  Cached
                </span>
                <span v-else class="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-xs rounded-full">Not Loaded</span>
              </div>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {{ model.description }}
              </p>
              <div class="flex gap-3 mt-2 text-xs text-gray-400">
                <span v-if="model.params" class="flex items-center gap-1">
                  <Zap class="w-3 h-3" />
                  {{ model.params }} params
                </span>
                <span v-if="model.disk_size" class="flex items-center gap-1">
                  <HardDrive class="w-3 h-3" />
                  {{ model.disk_size }}
                </span>
                <span v-if="model.ram_usage" class="flex items-center gap-1">
                  <Cpu class="w-3 h-3" />
                  {{ model.ram_usage }}
                </span>
                <span v-if="model.load_time">~{{ model.load_time }}</span>
              </div>
            </div>
          </label>
        </div>

        <!-- Cache Info -->
        <div class="mt-4 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg text-sm">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-gray-600 dark:text-gray-400">
                <span class="font-medium">Current model:</span> {{ currentModelInfo?.name || 'Not set' }}
              </p>
              <p class="text-gray-600 dark:text-gray-400 mt-1">
                <span class="font-medium">Cache:</span> {{ cachedModelsCount }}/{{ maxCachedModels }} models loaded
              </p>
            </div>
            <button
              class="px-3 py-1.5 text-xs font-medium bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
              :disabled="cachedModelsCount <= 1 || isLoading"
              @click="evictUnusedModels"
            >
              Evict Unused
            </button>
          </div>
        </div>

        <!-- Download Model Section -->
        <div class="mt-4 p-3 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-lg text-sm">
          <div class="flex items-start gap-3">
            <Download class="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
            <div class="flex-1">
              <h4 class="font-medium text-blue-900 dark:text-blue-200">Download Model</h4>
              <p class="text-xs text-blue-700 dark:text-blue-300 mt-1 mb-3">
                Download the default Qwen3-Embedding-0.6B model (~600MB). This is required for semantic search.
              </p>
              <button
                @click="showDownloadConfirm = true"
                :disabled="isLoading || downloadingModel !== null"
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Download v-if="!downloadingModel" class="w-3 h-3" />
                <Loader2 v-else class="w-3 h-3 animate-spin" />
                {{ downloadingModel ? 'Downloading...' : 'Download Qwen3-0.6B' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Re-index Section -->
        <div class="mt-4 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg text-sm">
          <div class="flex items-start gap-3">
            <Database class="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
            <div class="flex-1">
              <h4 class="font-medium text-amber-900 dark:text-amber-200">Rebuild TF-IDF Index</h4>
              <p class="text-xs text-amber-700 dark:text-amber-300 mt-1 mb-3">
                Rebuild the TF-IDF embeddings from scratch. This will re-process all files and may take some time.
              </p>
              <button
                @click="showReindexConfirm = true"
                :disabled="isLoading || reindexing"
                class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium rounded transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                <Database v-if="!reindexing" class="w-3 h-3" />
                <Loader2 v-else class="w-3 h-3 animate-spin" />
                {{ reindexing ? 'Rebuilding...' : 'Rebuild Index' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Download Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showDownloadConfirm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Download Model</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            This will download the Qwen3-Embedding-0.6B model from HuggingFace. The download is approximately 600MB and may take several minutes.
          </p>
          <div class="flex justify-end gap-3">
            <button
              @click="showDownloadConfirm = false"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              :disabled="downloadingModel !== null"
            >
              Cancel
            </button>
            <button
              @click="handleDownloadModel"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 transition-colors flex items-center gap-2"
              :disabled="downloadingModel !== null"
            >
              <Loader2 v-if="downloadingModel" class="w-4 h-4 animate-spin" />
              <Download v-else class="w-4 h-4" />
              {{ downloadingModel ? 'Downloading...' : 'Download' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Re-index Confirmation Modal -->
    <Teleport to="body">
      <div v-if="showReindexConfirm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Rebuild TF-IDF Index</h3>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Are you sure? This will rebuild all TF-IDF embeddings from scratch. This process may take some time depending on the number of files.
          </p>
          <div class="flex justify-end gap-3">
            <button
              @click="showReindexConfirm = false"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              :disabled="reindexing"
            >
              Cancel
            </button>
            <button
              @click="handleRebuildIndex"
              class="px-4 py-2 text-sm font-medium text-white bg-amber-600 rounded hover:bg-amber-700 transition-colors flex items-center gap-2"
              :disabled="reindexing"
            >
              <Loader2 v-if="reindexing" class="w-4 h-4 animate-spin" />
              <Database v-else class="w-4 h-4" />
              {{ reindexing ? 'Rebuilding...' : 'Rebuild' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
