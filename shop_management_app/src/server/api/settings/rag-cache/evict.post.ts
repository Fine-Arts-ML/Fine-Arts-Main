/**
 * Evict unused RAG models from cache.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const response = await $fetch(`${ragServiceUrl}/api/v1/rag/cache/evict`, {
      method: 'POST'
    })
    return response
  } catch (error: any) {
    console.error('Failed to evict cache:', error)
    throw createError({
      statusCode: 502,
      statusMessage: `Failed to evict cache: ${error.message || 'Service not responding'}`
    })
  }
})
