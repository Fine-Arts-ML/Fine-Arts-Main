/**
 * Generate Descriptions API
 * Calls OpenAI-compatible API directly from the Nuxt server to generate AI descriptions for images.
 * Eliminates the need for a Python microservice.
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

  // Read request body
  const body = await readBody(event)
  const {
    file_ids,
    max_tokens = maxTokens,
    temperature: reqTemperature = temperature
  }: {
    file_ids: number[]
    max_tokens?: number
    temperature?: number
  } = body

  // Validate inputs
  if (!file_ids || !Array.isArray(file_ids) || file_ids.length === 0) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid request: file_ids must be a non-empty array of numbers'
    })
  }

  if (!aiModel) {
    throw createError({
      statusCode: 500,
      statusMessage: 'AI model name is not configured. Please set AI_MODEL_NAME in .env'
    })
  }

  // Clamp values to reasonable ranges
  const clampedMaxTokens = Math.max(50, Math.min(4000, max_tokens))
  const clampedTemperature = Math.max(0, Math.min(2, temperature || reqTemperature))

  // Build the system prompt for descriptions
  const systemPrompt = `You are an expert art description writer. Analyze the provided image and write a detailed, descriptive paragraph that captures the essence of the artwork or photograph.

Guidelines:
- Write 2-4 sentences describing the image in detail
- Include: subject matter, artistic style, colors, composition, mood, and any notable details
- Use vivid, descriptive language
- Write in English
- Focus on what is visually present in the image
- Do not include tags, keywords, or metadata - write natural prose

Output Format:
- Return only the description paragraph
- Do NOT include any prefix, suffix, or formatting
- Do NOT include tags or semicolon-separated lists`

  // Nextcloud base URL for preview
  const ncBaseUrl = `http://${ncHost}:${ncPort}`

  console.log(`[generate-descriptions] Starting description generation for ${file_ids.length} file(s)`)
  console.log(`[generate-descriptions] AI Endpoint: ${aiEndpoint}`)
  console.log(`[generate-descriptions] Model: ${aiModel}`)
  console.log(`[generate-descriptions] Max Tokens: ${clampedMaxTokens}, Temperature: ${clampedTemperature}`)

  const results: Record<string, any> = {}

  // Process each file sequentially
  for (let i = 0; i < file_ids.length; i++) {
    const fileId = file_ids[i]

    try {
      console.log(`[generate-descriptions] Processing file ${i + 1}/${file_ids.length}: ${fileId}`)

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

      let fileName = ''

      try {
        const fileQuery = `
          SELECT name
          FROM oc_filecache
          WHERE fileid = $1::bigint
          LIMIT 1
        `
        const fileResult = await pool.query(fileQuery, [fileId])

        if (fileResult.rows.length > 0) {
          fileName = fileResult.rows[0].name
          console.log(`[generate-descriptions] File info: name=${fileName}`)
        }
      } catch (dbError: any) {
        console.warn(`[generate-descriptions] Could not query database for file ${fileId}: ${dbError.message}`)
      } finally {
        await pool.end()
      }

      // Step 2: Load image preview from Nextcloud
      let imageBase64 = ''
      try {
        const previewUrl = `${ncBaseUrl}/core/preview?fileId=${fileId}&x=1080&y=1080`
        console.log(`[generate-descriptions] Fetching preview: ${previewUrl}`)

        const response = await fetch(previewUrl, {
          method: 'GET',
          headers: {
            'Authorization': `Basic ${Buffer.from(`${ncAcc}:${ncPass}`).toString('base64')}`
          }
        })

        console.log(`[generate-descriptions] Preview response status: ${response.status}, ok: ${response.ok}`)

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`HTTP ${response.status}: ${errorText.substring(0, 300)}`)
        }

        const arrayBuffer = await response.arrayBuffer()
        const buffer = Buffer.from(arrayBuffer)
        imageBase64 = buffer.toString('base64')
        console.log(`[generate-descriptions] Preview loaded, size: ${buffer.length} bytes`)
      } catch (previewError: any) {
        console.error(`[generate-descriptions] Failed to load preview for file ${fileId}: ${previewError.message}`)

        results[fileId] = {
          file_id: fileId,
          file_name: fileName,
          description: '',
          raw_response: '',
          success: false,
          error: `Failed to load image preview: ${previewError.message}`
        }
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
              text: 'Analyze this image and write a detailed description paragraph.'
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

      // Build payload
      const payload: any = {
        model: aiModel,
        messages: messages,
        max_tokens: clampedMaxTokens,
        temperature: clampedTemperature,
        stream: false
      }

      // Build headers
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (aiApiKey) {
        headers['Authorization'] = `Bearer ${aiApiKey}`
      }

      // Step 4: Call the AI API
      console.log(`[generate-descriptions] Calling AI API...`)
      const aiResponse: any = await $fetch(aiEndpoint, {
        method: 'POST',
        headers,
        body: payload
      })

      console.log(`[generate-descriptions] Raw AI response keys: ${Object.keys(aiResponse || {})}`)

      // Step 5: Extract response text - handle multiple AI provider formats
      let textResponse = ''
      const choice = aiResponse?.choices?.[0]

      if (choice?.message?.content) {
        textResponse = choice.message.content
      } else if (choice?.message?.reasoning_content || choice?.message?.reasoning) {
        textResponse = choice.message.reasoning_content || choice.message.reasoning
        console.log(`[generate-descriptions] Detected thinking model response, using reasoning_content`)
      } else if (choice?.text) {
        textResponse = choice.text
      } else if (aiResponse?.response) {
        textResponse = aiResponse.response
      } else if (aiResponse?.generated_text) {
        textResponse = aiResponse.generated_text
      } else if (aiResponse?.result) {
        textResponse = aiResponse.result
      } else {
        console.error(`[generate-descriptions] Unexpected AI response structure:`, JSON.stringify(aiResponse).substring(0, 1000))
        throw new Error(`Unexpected API response format. Response keys: ${Object.keys(aiResponse || {}).join(', ')}`)
      }

      console.log(`[generate-descriptions] AI response: ${textResponse.substring(0, 200)}...`)

      results[fileId] = {
        file_id: fileId,
        file_name: fileName,
        description: textResponse,
        raw_response: textResponse,
        success: true
      }

    } catch (error: any) {
      console.error(`[generate-descriptions] Error processing file ${fileId}:`, error)
      results[fileId] = {
        file_id: fileId,
        file_name: '',
        description: '',
        raw_response: '',
        success: false,
        error: error.message || 'Unknown error occurred'
      }
    }
  }

  console.log(`[generate-descriptions] Description generation complete for ${file_ids.length} file(s)`)

  return {
    success: true,
    results
  }
})
