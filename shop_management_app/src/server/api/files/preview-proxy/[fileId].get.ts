/**
 * Proxy endpoint for fetching Nextcloud preview images with authentication.
 * 
 * The Nextcloud /core/preview endpoint requires Basic Auth, so we proxy the
 * request through this endpoint which adds the credentials.
 * 
 * Query parameters:
 *   - size: Image dimension (default: 64)
 *   - x: Custom width (overrides size)
 *   - y: Custom height (overrides size)
 */

import { Buffer } from 'buffer'

export default defineEventHandler(async (event) => {
  try {
    const fileId = getRouterParam(event, 'fileId')
    const size = parseInt(getQuery(event).size as string || '64', 10)
    const x = parseInt((getQuery(event).x as string) || String(size), 10)
    const y = parseInt((getQuery(event).y as string) || String(size), 10)

    if (!fileId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'fileId is required',
      })
    }

    const ncHost = process.env.NC_HOST || 'localhost'
    const ncAcc = process.env.NC_ACC || ''
    const ncPass = process.env.NC_PASS || ''

    // Construct the Nextcloud preview URL
    const previewUrl = `http://${ncHost}:8080/core/preview?fileId=${fileId}&x=${x}&y=${y}`

    console.log(`[preview-proxy] Fetching preview for fileId=${fileId}, x=${x}, y=${y}`)

    // Fetch the preview from Nextcloud with Basic Auth
    const response = await $fetch(previewUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Basic ${Buffer.from(`${ncAcc}:${ncPass}`).toString('base64')}`,
      },
      responseType: 'blob',
    })

    // Set appropriate content type headers
    if (response instanceof Blob) {
      const contentType = response.type || 'image/jpeg'
      setHeader(event, 'Content-Type', contentType)
      setHeader(event, 'Cache-Control', 'public, max-age=3600')
      
      // Convert blob to buffer and return
      const buffer = Buffer.from(await response.arrayBuffer())
      return buffer
    }

    // If response is already a buffer/arraybuffer
    if (Buffer.isBuffer(response) || Array.isArray(response)) {
      setHeader(event, 'Content-Type', 'image/jpeg')
      setHeader(event, 'Cache-Control', 'public, max-age=3600')
      return response
    }

    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to process preview image',
    })
  } catch (error: any) {
    console.error('[preview-proxy] Error:', error)
    if (error.statusCode) throw error
    
    // Handle 404 from Nextcloud (no preview available)
    if (error.statusCode === 404) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Preview not available',
      })
    }

    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch preview',
      data: error.message,
    })
  }
})
