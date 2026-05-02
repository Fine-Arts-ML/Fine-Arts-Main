/**
 * RAG Search API endpoint - Proxy to Python RAG service.
 *
 * Performs semantic search using TF-IDF weighted embeddings.
 *
 * Request body:
 *   - query: Search query (required)
 *   - top_k: Max results per page (default: 24)
 *   - previewSize: Preview dimension (default: 540)
 *   - min_similarity: Minimum similarity threshold (default: 0.25)
 *   - offset: Pagination offset (default: 0)
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { query, top_k = 24, previewSize = 540, min_similarity = 0.25, offset = 0 } = body

  if (!query || !query.trim()) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Query is required'
    })
  }

  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const ragResponse = await $fetch(`${ragServiceUrl}/api/v1/rag/search`, {
      method: 'POST',
      body: {
        query: query.trim(),
        top_k,
        preview_size: previewSize,
        min_similarity,
        offset
      }
    })

    return ragResponse
  } catch (error: any) {
    console.error('RAG search failed:', error)
    throw createError({
      statusCode: 502,
      statusMessage: `RAG service unavailable: ${error.message || 'Service not responding'}`
    })
  }
})
