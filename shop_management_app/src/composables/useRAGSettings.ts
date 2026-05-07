/**
 * Composable for RAG Search settings management.
 *
 * Handles model selection, cache configuration, and model cache operations.
 */

import { ref, computed } from 'vue'

export interface RAGModel {
  id: string
  name: string
  description: string
  params: string
  disk_size: string
  ram_usage: string
  load_time: string
  downloaded: boolean
  in_cache: boolean
}

export interface CacheConfig {
  max_cached: number
  current_count: number
  cached_models: string[]
}

export interface CurrentModel {
  current_model: string | null
  model_info: {
    id: string
    name: string
    description: string
  } | null
}

export function useRAGSettings() {
  const selectedModel = ref<string>('')
  const maxCachedModels = ref(1)
  const cachedModelsCount = ref(0)
  const cachedModelsList = ref<string[]>([])
  const models = ref<RAGModel[]>([])
  const currentModelInfo = ref<CurrentModel['model_info']>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  /**
   * Load all RAG settings from the server.
   */
  async function loadSettings() {
    isLoading.value = true
    error.value = null

    try {
      const [modelsResponse, cacheResponse, currentResponse] = await Promise.all([
        $fetch<RAGModel[]>('/api/settings/rag-models'),
        $fetch<CacheConfig>('/api/settings/rag-cache-config'),
        $fetch<CurrentModel>('/api/settings/rag-model/current')
      ])

      models.value = modelsResponse
      maxCachedModels.value = cacheResponse.max_cached
      cachedModelsCount.value = cacheResponse.current_count
      cachedModelsList.value = cacheResponse.cached_models
      currentModelInfo.value = currentResponse.model_info
      selectedModel.value = currentResponse.current_model || modelsResponse[0]?.id || ''
    } catch (err: any) {
      error.value = err.message || 'Failed to load settings'
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Switch to a different model.
   *
   * @param modelId - The model ID to switch to
   */
  async function switchModel(modelId: string) {
    isLoading.value = true
    error.value = null

    try {
      await $fetch('/api/settings/rag-model', {
        method: 'POST',
        body: { modelId }
      })

      selectedModel.value = modelId
      await loadSettings()
    } catch (err: any) {
      error.value = err.message || 'Failed to switch model'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update the maximum number of cached models.
   *
   * @param maxCached - New max cached value
   */
  async function updateCacheConfig(maxCached: number) {
    isLoading.value = true
    error.value = null

    try {
      await $fetch('/api/settings/rag-cache-config', {
        method: 'POST',
        body: { maxCached }
      })

      maxCachedModels.value = maxCached
      await loadSettings()
    } catch (err: any) {
      error.value = err.message || 'Failed to update cache config'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Evict unused models from cache.
   */
  async function evictUnusedModels() {
    isLoading.value = true
    error.value = null

    try {
      await $fetch('/api/settings/rag-cache/evict', {
        method: 'POST'
      })

      await loadSettings()
    } catch (err: any) {
      error.value = err.message || 'Failed to evict models'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Check if a model is currently in cache.
   */
  function isInCache(modelId: string): boolean {
    return cachedModelsList.value.includes(modelId)
  }

  /**
   * Download a model from HuggingFace.
   *
   * @param modelId - The model ID to download
   * @param hfUrl - Optional HuggingFace URL (defaults to Qwen model pattern)
   */
  async function downloadModel(modelId: string, hfUrl?: string) {
    isLoading.value = true
    error.value = null

    try {
      const result = await $fetch<{ status: string; message: string; model: RAGModel }>('/api/settings/rag-model/download', {
        method: 'POST',
        body: { modelId, hfUrl: hfUrl || '' }
      })

      // Reload settings to update the models list
      await loadSettings()
      return result
    } catch (err: any) {
      error.value = err.message || 'Failed to download model'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Rebuild the TF-IDF index from scratch.
   */
  async function rebuildIndex() {
    isLoading.value = true
    error.value = null

    try {
      const result = await $fetch<{ status: string; message: string; index_size: number }>('/api/settings/rag-index/rebuild', {
        method: 'POST'
      })

      return result
    } catch (err: any) {
      error.value = err.message || 'Failed to rebuild index'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  return {
    selectedModel,
    maxCachedModels,
    cachedModelsCount,
    cachedModelsList,
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
  }
}
