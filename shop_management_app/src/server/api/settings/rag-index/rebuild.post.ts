/**
 * Rebuild the TF-IDF index.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const result = await $fetch(`${ragServiceUrl}/api/v1/rag/index/rebuild`, {
      method: 'POST'
    })
    return result
  } catch (error: any) {
    console.error('Failed to rebuild index:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.data?.message || error.message || 'Failed to rebuild index'
    })
  }
})
