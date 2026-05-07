/**
 * Update RAG model cache configuration.
 * Proxies to Python RAG service.
 *
 * Request body:
 *   - maxCached: Maximum number of models to cache
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { maxCached } = body

  if (maxCached === undefined || maxCached < 1 || maxCached > 5) {
    throw createError({
      statusCode: 400,
      statusMessage: 'maxCached must be between 1 and 5'
    })
  }

  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const response = await $fetch(`${ragServiceUrl}/api/v1/rag/cache/config`, {
      method: 'POST',
      body: { max_cached: maxCached }
    })
    return response
  } catch (error: any) {
    console.error('Failed to update cache config:', error)
    throw createError({
      statusCode: 502,
      statusMessage: `Failed to update cache config: ${error.message || 'Service not responding'}`
    })
  }
})
