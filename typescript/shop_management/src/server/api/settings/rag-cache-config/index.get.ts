/**
 * Get RAG model cache configuration.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const config = await $fetch(`${ragServiceUrl}/api/v1/rag/cache/config`)
    return config
  } catch (error: any) {
    console.error('Failed to fetch cache config:', error)
    return {
      max_cached: parseInt(process.env.MAX_CACHED_MODELS || '1', 10),
      current_count: 0,
      cached_models: []
    }
  }
})
