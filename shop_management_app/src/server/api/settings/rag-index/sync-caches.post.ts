/**
 * Sync Caches API
 * Proxies to Python tag service to synchronize bre_* caches with oc_* tables
 */

export default defineEventHandler(async (event) => {
  const tagServiceUrl = process.env.TAG_SERVICE_URL || 'http://localhost:8000'
  const body = await readBody(event)
  
  const { sync_type }: { sync_type?: 'tag_cache' | 'mapping_index' | 'file_tracker' | 'full' } = body

  try {
    const result = await $fetch(`${tagServiceUrl}/api/sync-caches`, {
      method: 'POST',
      body: sync_type ? { sync_type } : {}
    })
    return result
  } catch (error: any) {
    throw createError({
      statusCode: error.statusCode || 500,
      statusMessage: error.message || 'Failed to sync caches',
      data: error.data
    })
  }
})
