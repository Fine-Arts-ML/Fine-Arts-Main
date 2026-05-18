/**
 * Apply Tags API
 * Proxies to Python tag service to apply tags to files
 */

export default defineEventHandler(async (event) => {
  const tagServiceUrl = process.env.TAG_SERVICE_URL || 'http://localhost:8000'
  const body = await readBody(event)
  
  const { file_id, tag_ids }: { file_id: number, tag_ids: number[] } = body
  if (!file_id || !tag_ids || !Array.isArray(tag_ids)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameters: file_id (number) and tag_ids (array of numbers)'
    })
  }

  try {
    const result = await $fetch(`${tagServiceUrl}/api/apply-tags`, {
      method: 'POST',
      body: { file_id, tag_ids }
    })
    return result
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to apply tags',
      data: error.data
    })
  }
})
