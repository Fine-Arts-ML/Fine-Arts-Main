/**
 * List available RAG models.
 * Proxies to Python RAG service.
 */

export default defineEventHandler(async (event) => {
  const ragServiceUrl = process.env.RAG_SERVICE_URL || 'http://localhost:8079'

  try {
    const models = await $fetch<any[]>(`${ragServiceUrl}/api/v1/rag/models`)
    return models
  } catch (error: any) {
    console.error('Failed to fetch RAG models:', error)
    // Return fallback model list if RAG service is unavailable
    return [
      {
        id: 'qwen3-0.6b',
        name: 'Qwen3-0.6B',
        description: 'Best accuracy, recommended for production',
        params: '600M',
        disk_size: '~1.2GB',
        ram_usage: '~1.5GB',
        load_time: '~10 seconds',
        downloaded: true,
        in_cache: false
      }
    ]
  }
})
