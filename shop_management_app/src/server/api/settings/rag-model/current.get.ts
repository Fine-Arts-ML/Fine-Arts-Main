/**
 * Get current active RAG model.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const response = await $fetch(`${ragServiceUrl}/api/v1/rag/models/current`)
    return response
  } catch (error: any) {
    console.error('Failed to fetch current model:', error)
    return {
      current_model: process.env.DEFAULT_MODEL || 'qwen3-0.6b',
      model_info: null
    }
  }
})
