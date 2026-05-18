/**
 * Cleanse Tags API
 * Proxies to Python tag service to clean and normalize tags
 */

export default defineEventHandler(async (event) => {
  const tagServiceUrl = process.env.TAG_SERVICE_URL || 'http://localhost:8000'
  const body = await readBody(event)
  
  const { tags }: { tags?: string[] } = body
  if (!tags || !Array.isArray(tags)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: tags (array of strings)'
    })
  }

  try {
    const result = await $fetch(`${tagServiceUrl}/api/cleanse-tags`, {
      method: 'POST',
      body: { tags }
    })
    return result
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to cleanse tags',
      data: error.data
    })
  }
})
