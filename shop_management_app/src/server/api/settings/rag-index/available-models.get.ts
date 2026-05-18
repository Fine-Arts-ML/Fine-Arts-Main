/**
 * Available Models API
 * Fetches available models from the OpenAI-compatible API endpoint.
 */

export default defineEventHandler(async (event) => {
  const aiEndpoint = process.env.AI_MODEL_ENDPOINT || 'http://localhost:8080/v1/chat/completions'
  const aiApiKey = process.env.AI_API_KEY || ''

  // Extract the base URL (remove /v1/chat/completions to get the base)
  // e.g., http://localhost:8080/v1/chat/completions -> http://localhost:8080
  const baseEndpoint = aiEndpoint.replace('/v1/chat/completions', '')
  const modelsUrl = `${baseEndpoint}/v1/models`

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    
    if (aiApiKey) {
      headers['Authorization'] = `Bearer ${aiApiKey}`
    }

    const response: any = await $fetch(modelsUrl, {
      method: 'GET',
      headers
    })

    // Normalize response format (OpenAI-compatible)
    const models = response.data || response.models || []
    
    const normalizedModels = models.map((m: any) => ({
      id: m.id || m.model || '',
      name: m.id || m.model || '',
      object: m.object || 'model',
      ownedBy: m.owned_by || m.ownedBy || ''
    })).filter((m: any) => m.id)

    return {
      success: true,
      models: normalizedModels
    }
  } catch (error: any) {
    console.error('[available-models] Failed to fetch models:', error.message)
    
    // Return empty array with error info - don't throw, let the UI handle gracefully
    return {
      success: false,
      models: [],
      error: error.message || 'Failed to fetch models'
    }
  }
})
