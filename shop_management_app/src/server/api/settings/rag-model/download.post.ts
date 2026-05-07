/**
 * Download a model from HuggingFace.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'
  const body = await readBody(event)
  const { modelId, hfUrl } = body || {}

  if (!modelId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'modelId is required'
    })
  }

  try {
    const result = await $fetch(`${ragServiceUrl}/api/v1/rag/models/download`, {
      method: 'POST',
      body: { model_id: modelId, hf_url: hfUrl || '' }
    })
    return result
  } catch (error: any) {
    console.error('Failed to download model:', error)
    throw createError({
      statusCode: 500,
      statusMessage: error.data?.message || error.message || 'Failed to download model'
    })
  }
})
