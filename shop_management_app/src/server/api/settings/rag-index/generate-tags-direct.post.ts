/**
 * Generate Tags Direct API
 * Calls OpenAI-compatible API directly from the Nuxt server to generate tags for images.
 * Eliminates the need for a Python microservice.
 *
 * Supports streaming progress updates via Server-Sent Events (SSE) when stream_progress=true.
 */

import { Pool } from 'pg'
import { $fetch } from 'ofetch'

export default defineEventHandler(async (event: any) => {
  // Get configuration from environment variables
  const aiEndpoint = process.env.AI_MODEL_ENDPOINT || 'http://localhost:8080/v1/chat/completions'
  const aiModel = process.env.AI_MODEL_NAME || ''
  const aiApiKey = process.env.AI_API_KEY || ''
  const maxTokens = parseInt(process.env.AI_MAX_TOKENS || '3000')
  const temperature = parseFloat(process.env.AI_TEMPERATURE || '0.1')
  
  // Nextcloud configuration
  const ncHost = process.env.NC_HOST || 'localhost'
  const ncPort = parseInt(process.env.NC_PORT || '8080')
  const ncAcc = process.env.NC_ACC || 'Tom'
  const ncPass = process.env.NC_PASS || ''
  
  // Tag generation defaults
  const defaultMaxTags = parseInt(process.env.TAG_MAX_COUNT || '20')
  const defaultTemperature = parseFloat(process.env.AI_TEMPERATURE || '0.1')
  const defaultMaxTokens = parseInt(process.env.AI_MAX_TOKENS || '3000')

  // Read request body
  const body = await readBody(event)
  const {
    file_ids,
    max_tags = defaultMaxTags,
    temperature: reqTemperature = defaultTemperature,
    max_tokens = defaultMaxTokens,
    thinking_enabled = true,
    custom_prompt,
    stream_progress = false  // Enable streaming progress updates
  }: {
    file_ids: string[]
    max_tags?: number
    temperature?: number
    max_tokens?: number
    thinking_enabled?: boolean
    custom_prompt?: string
    stream_progress?: boolean
  } = body

  // Validate inputs
  if (!file_ids || !Array.isArray(file_ids) || file_ids.length === 0) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid request: file_ids must be a non-empty array of strings'
    })
  }

  if (!aiModel) {
    throw createError({
      statusCode: 500,
      statusMessage: 'AI model name is not configured. Please set AI_MODEL_NAME in .env'
    })
  }

  // Clamp values to reasonable ranges
  const clampedMaxTags = Math.max(1, Math.min(100, max_tags))
  const clampedTemperature = Math.max(0, Math.min(2, temperature || reqTemperature))
  const clampedMaxTokens = Math.max(50, Math.min(4000, max_tokens || defaultMaxTokens))

  // Build the system prompt
  const systemPrompt = custom_prompt || `You are an expert art tagging assistant. Analyze the provided image and return relevant tags for cataloging artwork and photographs.

Guidelines:
- Generate between ${clampedMaxTags} tags per image (no more, no less than ${clampedMaxTags})
- Consider: subject matter, artistic style, medium, colors, composition, lighting, mood, technique
- Tags should be specific, descriptive, and in English
- Use lowercase for all tags
- Use multi-word tags separated by spaces (e.g., "oil painting", "landscape view")
- Include both broad categories and specific details

Output Format:
- Return tags as a semicolon-separated list ONLY
- Use semicolon with optional spaces as separator: Tag1 ; Tag 2 ; Tag3
- Do NOT include any additional text, explanations, formatting, or markdown
- Do NOT include brackets, quotes, or any other delimiters
- Only return the raw tag string

Example output:
portrait ; oil painting ; warm tones ; vibrant ; impressionist ; indoor lighting ; close-up ; expressive ; canvas art ; human subject`

  // Nextcloud base URL for preview
  const ncBaseUrl = `http://${ncHost}:${ncPort}`

  console.log(`[generate-tags-direct] Starting tag generation for ${file_ids.length} file(s)`)
  console.log(`[generate-tags-direct] AI Endpoint: ${aiEndpoint}`)
  console.log(`[generate-tags-direct] Model: ${aiModel}`)
  console.log(`[generate-tags-direct] Max Tags: ${clampedMaxTags}, Temperature: ${clampedTemperature}, Max Tokens: ${clampedMaxTokens}`)
  console.log(`[generate-tags-direct] Stream progress: ${stream_progress}`)

  const results: Record<string, any> = {} as Record<string, any>

  // If streaming is enabled, set up SSE response
  if (stream_progress) {
    event.node.res.setHeader('Content-Type', 'text/event-stream')
    event.node.res.setHeader('Cache-Control', 'no-cache')
    event.node.res.setHeader('Connection', 'keep-alive')
    event.node.res.setHeader('X-Accel-Buffering', 'no')
  }

  // Helper to send SSE event
  const sendSSE = (data: any) => {
    if (!stream_progress) return
    const eventData = `data: ${JSON.stringify(data)}\n\n`
    event.node.res.write(eventData)
  }

  // Helper to check if aborted
  const isAborted = () => {
    return (event as any).context?.aborted === true
  }

  // Process each file sequentially
  for (let i = 0; i < file_ids.length; i++) {
    // Check for abort before processing each file
    if (isAborted()) {
      console.log(`[generate-tags-direct] Aborted by user after processing ${i}/${file_ids.length} files`)
      sendSSE({ type: 'abort', processed: i, total: file_ids.length, results })
      if (stream_progress) {
        event.node.res.end()
      }
      return { success: true, results, aborted: true }
    }

    const fileId = file_ids[i]
    
    try {
      console.log(`[generate-tags-direct] Processing file ${i + 1}/${file_ids.length}: ${fileId}`)
      
      // Send progress update: processing started
      sendSSE({
        type: 'progress',
        current: i + 1,
        total: file_ids.length,
        fileId: fileId,
        fileName: '',
        status: 'processing'
      })

      // Step 1: Get file info from database to find the path
      const dbHost = process.env.DB_HOST || 'localhost'
      const dbPort = parseInt(process.env.DB_PORT || '5432')
      const dbName = process.env.DB_NAME || 'nextpsql'
      const dbUser = process.env.DB_USER || 'nextuser'
      const dbPassword = process.env.DB_PASSWORD || ''

      const pool = new Pool({
        host: dbHost,
        port: dbPort,
        database: dbName,
        user: dbUser,
        password: dbPassword,
      })

      let filePath = ''
      let fileName = ''

      try {
        // Query the Nextcloud oc_filecache table to get the path
        const fileQuery = `
          SELECT path, name
          FROM oc_filecache
          WHERE fileid = $1::bigint
          LIMIT 1
        `
        const fileResult = await pool.query(fileQuery, [fileId])
        
        if (fileResult.rows.length > 0) {
          const fileInfo = fileResult.rows[0]
          fileName = fileInfo.name
          // Path is like "Tom/Some Folder/image.jpg", we need just the relative part
          filePath = fileInfo.path
          console.log(`[generate-tags-direct] File info: name=${fileName}, path=${filePath}`)
        }
      } catch (dbError: any) {
        console.warn(`[generate-tags-direct] Could not query database for file ${fileId}: ${dbError.message}`)
      } finally {
        await pool.end()
      }

      // Step 2: Load image preview from Nextcloud using native fetch
      // We use native fetch because $fetch (ofetch) doesn't support responseType in Node.js server routes
      let imageBase64 = ''
      try {
        const previewUrl = `${ncBaseUrl}/core/preview?fileId=${fileId}&x=1080&y=1080`
        console.log(`[generate-tags-direct] Fetching preview: ${previewUrl}`)

        const response = await fetch(previewUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Basic ${Buffer.from(`${ncAcc}:${ncPass}`).toString('base64')}`
          }
        })

        console.log(`[generate-tags-direct] Preview response status: ${response.status}, ok: ${response.ok}`)

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 300)}`)
        }

        const arrayBuffer = await response.arrayBuffer()
        const buffer = Buffer.from(arrayBuffer)
        imageBase64 = buffer.toString('base64')
        console.log(`[generate-tags-direct] Preview loaded, size: ${buffer.length} bytes`)
      } catch (previewError: any) {
        console.error(`[generate-tags-direct] Failed to load preview for file ${fileId}: ${previewError.message}`)
        
        results[fileId] = {
          file_id: fileId,
          file_name: fileName,
          tags: [],
          raw_response: '',
          success: false,
          error: `Failed to load image preview: ${previewError.message}`
        }
        
        sendSSE({
          type: 'result',
          current: i + 1,
          total: file_ids.length,
          fileId: fileId,
          fileName: fileName,
          success: false,
          error: `Failed to load image preview: ${previewError.message}`,
          tags: []
        })
        continue
      }

      // Step 3: Build the API request
      const messages = [
        {
          role: 'system' as const,
          content: systemPrompt
        },
        {
          role: 'user' as const,
          content: [
            {
              type: 'text' as const,
              text: custom_prompt || `Analyze this image and generate tags. Return exactly ${clampedMaxTags} tags as a semicolon-separated list.`
            },
            {
              type: 'image_url' as const,
              image_url: {
                url: `data:image/jpeg;base64,${imageBase64}`
              }
            }
          ]
        }
      ]

      // Build payload based on provider
      const payload: any = {
        model: aiModel,
        messages: messages,
        max_tokens: clampedMaxTokens,
        temperature: clampedTemperature,
        stream: false
      }

      // Add thinking parameters if enabled
      if (thinking_enabled) {
        // Some models support 'thinking' or 'reasoning' parameters
        // This is provider-specific, so we add it conditionally
        payload.extra_body = { thinking: true }
      }

      // Build headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (aiApiKey) {
        headers['Authorization'] = `Bearer ${aiApiKey}`
      }

      // Step 4: Call the AI API
      console.log(`[generate-tags-direct] Calling AI API...`)
      const aiResponse: any = await $fetch(aiEndpoint, {
        method: 'POST',
        headers,
        body: payload
      })

      console.log(`[generate-tags-direct] Raw AI response keys: ${Object.keys(aiResponse || {})}`)
      console.log(`[generate-tags-direct] Raw AI response structure: ${JSON.stringify(aiResponse).substring(0, 500)}`)

      // Step 5: Extract response text - handle multiple AI provider formats
      let textResponse = ''
      const choice = aiResponse?.choices?.[0]
      
      if (choice?.message?.content) {
        // OpenAI/vLLM/TGI format: { choices: [{ message: { content: "..." } }] }
        textResponse = choice.message.content
      } else if (choice?.message?.reasoning_content || choice?.message?.reasoning) {
        // Thinking/reasoning model: content is empty, reasoning is in reasoning_content
        // Use the reasoning_content as the response (it contains the actual output for thinking models)
        textResponse = choice.message.reasoning_content || choice.message.reasoning
        console.log(`[generate-tags-direct] Detected thinking model response, using reasoning_content`)
      } else if (choice?.text) {
        // Alternative OpenAI format: { choices: [{ text: "..." }] }
        textResponse = choice.text
      } else if (aiResponse?.response) {
        // Ollama format: { response: "..." }
        textResponse = aiResponse.response
      } else if (aiResponse?.generated_text) {
        // HuggingFace TGI format: { generated_text: "..." }
        textResponse = aiResponse.generated_text
      } else if (aiResponse?.result) {
        // Simple format: { result: "..." }
        textResponse = aiResponse.result
      } else {
        // Debug: log the full response for troubleshooting
        console.error(`[generate-tags-direct] Unexpected AI response structure:`, JSON.stringify(aiResponse).substring(0, 1000))
        throw new Error(`Unexpected API response format. Response keys: ${Object.keys(aiResponse || {}).join(', ')}`)
      }

      console.log(`[generate-tags-direct] AI response: ${textResponse.substring(0, 200)}...`)

      // Step 6: Parse the semicolon-separated tags
      const rawTags = textResponse
        .split(';')
        .map((tag: string) => tag.trim())
        .filter((tag: string) => tag.length > 0)
        .slice(0, clampedMaxTags)

      console.log(`[generate-tags-direct] Generated ${rawTags.length} tags for file ${fileId}`)

      results[fileId] = {
        file_id: fileId,
        file_name: fileName,
        tags: rawTags,
        raw_response: textResponse,
        success: true
      }

      // Send result via SSE
      sendSSE({
        type: 'result',
        current: i + 1,
        total: file_ids.length,
        fileId: fileId,
        fileName: fileName,
        success: true,
        tags: rawTags
      })

    } catch (error: any) {
      console.error(`[generate-tags-direct] Error processing file ${fileId}:`, error)
      results[fileId] = {
        file_id: fileId,
        file_name: '',
        tags: [],
        raw_response: '',
        success: false,
        error: error.message || 'Unknown error occurred'
      }
      
      sendSSE({
        type: 'result',
        current: i + 1,
        total: file_ids.length,
        fileId: fileId,
        fileName: '',
        success: false,
        error: error.message || 'Unknown error occurred',
        tags: []
      })
    }
  }

  // Send completion event
  sendSSE({
    type: 'complete',
    total: file_ids.length,
    results: Object.values(results).filter((r: any) => r.success).length
  })

  if (stream_progress) {
    event.node.res.end()
  }

  console.log(`[generate-tags-direct] Tag generation complete for ${file_ids.length} file(s)`)

  return {
    success: true,
    results
  }
})
