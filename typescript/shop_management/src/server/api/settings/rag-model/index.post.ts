/**
 * Switch RAG model.
 * Proxies to Python RAG service.
 *
 * Request body:
 *   - modelId: The model ID to switch to
 */

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  const { modelId } = body

  if (!modelId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'modelId is required'
    })
  }

  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const response = await $fetch(`${ragServiceUrl}/api/v1/rag/models/switch`, {
      method: 'POST',
      body: { model_id: modelId }
    })
    return response
  } catch (error: any) {
    console.error('Failed to switch model:', error)
    throw createError({
      statusCode: 502,
      statusMessage: `Failed to switch model: ${error.message || 'Service not responding'}`
    })
  }
})
