/**
 * List Tags API
 * Proxies to Python tag service to list all tags from the cache
 */

export default defineEventHandler(async (event) => {
  const tagServiceUrl = process.env.TAG_SERVICE_URL || 'http://localhost:8000'

  try {
    const result = await $fetch(`${tagServiceUrl}/api/list-tags`, {
      method: 'GET'
    })
    return result
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to list tags',
      data: error.data
    })
  }
})
