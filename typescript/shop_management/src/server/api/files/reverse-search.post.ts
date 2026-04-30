/**
 * Reverse image search using perceptual hashing.
 *
 * Accepts an uploaded image, calculates hashes via Python subprocess,
 * and returns the closest matches from the database.
 *
 * Request Body: multipart/form-data
 *   - image: Uploaded image file
 *   - hashMethod: One of 'whash', 'ahash', 'phash', 'average'
 *
 * Reuses transformPreviewUrls from ~/server/utils/preview for preview URL conversion.
 */

import { transformPreviewUrls } from '~/server/utils/preview'
import { spawn } from 'child_process'
import { Buffer } from 'buffer'
import path from 'path'

interface HashResult {
  whash: string
  ahash: string
  phash: string
  error?: string
}

/**
 * Calculate Hamming distance between two hex hash strings.
 * Each hex char = 4 bits, so we XOR the bit representations.
 * Uses a lookup table for popcount to avoid BigInt (not available in ES2019).
 */
function hexHammingDistance(hex1: string, hex2: string): number {
  // XOR the hex values as 64-bit unsigned integers
  // Split into two 32-bit parts to avoid floating point issues
  const high1 = parseInt(hex1.substring(0, 8), 16)
  const low1 = parseInt(hex1.substring(8, 16), 16)
  const high2 = parseInt(hex2.substring(0, 8), 16)
  const low2 = parseInt(hex2.substring(8, 16), 16)
  
  const xorHigh = high1 ^ high2
  const xorLow = low1 ^ low2
  
  // Popcount using lookup table
  const table = [0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4]
  function popcount(n: number): number {
    let count = 0
    while (n) {
      count += table[n & 0xF]
      n >>>= 4
    }
    return count
  }
  
  return popcount(xorHigh) + popcount(xorLow)
}

function calculateHashes(imageBuffer: Buffer): Promise<HashResult> {
  return new Promise((resolve, reject) => {
    // Use the venv Python to ensure imagehash library is available
    const baseDir = process.cwd().replace('/src/server/api/files', '')
    const venvPython = path.join(baseDir, '.venv', 'bin', 'python')
    const pythonScript = path.join(baseDir, 'src', 'py-code', 'hash_helper.py')
    
    console.log('[reverse-search] Base dir:', baseDir)
    console.log('[reverse-search] Python path:', venvPython)
    console.log('[reverse-search] Script path:', pythonScript)
    
    const python = spawn(venvPython, [pythonScript])

    let stdout = ''
    let stderr = ''

    python.stdout.on('data', (data: Buffer) => {
      stdout += data.toString()
      console.log('[reverse-search] Python stdout:', data.toString().substring(0, 100))
    })

    python.stderr.on('data', (data: Buffer) => {
      stderr += data.toString()
      console.log('[reverse-search] Python stderr:', data.toString())
    })

    python.on('close', (code) => {
      console.log('[reverse-search] Python process closed with code:', code)
      console.log('[reverse-search] Full stdout:', stdout)
      console.log('[reverse-search] Full stderr:', stderr)
      
      if (code !== 0 && code !== null) {
        reject(new Error(`Python process exited with code ${code}: ${stderr}`))
        return
      }

      try {
        const b64Json = stdout.trim()
        if (!b64Json) {
          reject(new Error('Python script produced no output'))
          return
        }
        const jsonStr = Buffer.from(b64Json, 'base64').toString('utf-8')
        console.log('[reverse-search] Parsed JSON:', jsonStr)
        const result: HashResult = JSON.parse(jsonStr)
        
        if (result.error) {
          reject(new Error(result.error))
        } else {
          resolve(result)
        }
      } catch (e) {
        reject(new Error(`Failed to parse hash result: ${e}`))
      }
    })

    python.on('error', (err) => {
      console.log('[reverse-search] Python process error:', err.message)
      reject(new Error(`Failed to start Python process: ${err.message}`))
    })

    const b64Data = imageBuffer.toString('base64')
    console.log('[reverse-search] Image size:', imageBuffer.length, 'bytes')
    console.log('[reverse-search] Base64 length:', b64Data.length)
    python.stdin.write(b64Data)
    python.stdin.end()
  })
}

export default defineEventHandler(async (event: any) => {
  const formData = await readMultipartFormData(event)
  
  // Extract hashMethod from formData (it's part of the multipart data)
  const hashMethodField = formData?.find(f => f.name === 'hashMethod')
  const hashMethod = hashMethodField ? hashMethodField.data.toString('utf-8') : 'whash'

  const validMethods = ['whash', 'ahash', 'phash', 'average']
  if (!validMethods.includes(hashMethod)) {
    throw createError({
      statusCode: 400,
      statusMessage: `Invalid hash method: ${hashMethod}. Must be one of: ${validMethods.join(', ')}`,
    })
  }

  const imageField = formData?.find(f => f.name === 'image')
  if (!imageField) {
    throw createError({ statusCode: 400, statusMessage: 'Image is required' })
  }

  if (!imageField.data || !Buffer.isBuffer(imageField.data)) {
    throw createError({ statusCode: 400, statusMessage: 'Invalid image data' })
  }

  // Calculate hashes using Python
  let hashes: HashResult
  try {
    hashes = await calculateHashes(imageField.data)
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to calculate hashes',
      data: error.message,
    })
  }

  if (hashes.error) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Hash calculation failed',
      data: hashes.error,
    })
  }

  const pg = await import('pg')
  const pool = new pg.Pool({
    host: process.env.DB_HOST || 'localhost',
    port: Number(process.env.DB_PORT) || 5432,
    database: process.env.DB_NAME || 'shop_management',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
  })

  try {
    console.log('[reverse-search] Starting database query...')
    console.log('[reverse-search] Hashes:', JSON.stringify(hashes))
    console.log('[reverse-search] Hash method:', hashMethod)
    
    const previewSize = 540

    // Query all hashes with their distances computed in JavaScript
    // We fetch all rows and sort client-side since hamming_distance function doesn't exist
    // Removed LIMIT to match Streamlit app behavior - all 1517+ rows must be scanned
    const allMatchesQuery = `
      SELECT
        h.id AS "fileId",
        ai.name AS "filename",
        ai.preview_url AS "previewUrl",
        dn.display_name AS "displayName",
        h.w_hash,
        h.a_hash,
        h.p_hash
      FROM bre_hashes h
      INNER JOIN bre_advance_index ai ON h.id = ai.fileid::text
      LEFT JOIN bre_display_name_index dni ON h.id = dni.file_id
      LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
    `

    const allMatchesResult = await pool.query(allMatchesQuery)
    const allRows = (allMatchesResult as any).rows as Array<{
      fileId: number
      filename: string
      previewUrl: string
      displayName: string | null
      w_hash: string
      a_hash: string
      p_hash: string
    }>
    
    console.log('[reverse-search] Fetched', allRows.length, 'rows from database')

    await pool.end()

    // Compute hamming distances client-side
    // Use min(whash, ahash, phash) as the ranking metric to match Streamlit app behavior
    const rowsWithDistance = allRows
      .filter(row => row.w_hash && row.a_hash && row.p_hash) // Skip rows with NULL hashes
      .map(row => {
        const whashDist = hexHammingDistance(hashes.whash, row.w_hash)
        const ahashDist = hexHammingDistance(hashes.ahash, row.a_hash)
        const phashDist = hexHammingDistance(hashes.phash, row.p_hash)
        
        // Use minimum distance across all hash methods for ranking
        // This ensures identical images are always found (at least one hash will show distance 0)
        const minDistance = Math.min(whashDist, ahashDist, phashDist)
        
        return {
          ...row,
          whash_distance: String(whashDist),
          ahash_distance: String(ahashDist),
          phash_distance: String(phashDist),
          minDistance
        }
      })

    // Sort by minimum distance for initial ranking (matching Streamlit app ranking logic)
    rowsWithDistance.sort((a, b) => a.minDistance - b.minDistance)

    // Transform preview URLs
    const top10 = rowsWithDistance.slice(0, 10)

    // Re-sort by selected hash method for display (matching Streamlit app behavior)
    // The Streamlit app uses the hash type selector to re-sort results for display
    const hashMethodColumnMap: Record<string, string> = {
      whash: 'whash_distance',
      ahash: 'ahash_distance',
      phash: 'phash_distance',
    }
    
    if (hashMethod in hashMethodColumnMap) {
      const column = hashMethodColumnMap[hashMethod]
      top10.sort((a, b) => parseInt(a[column], 10) - parseInt(b[column], 10))
    }
    const transformed = transformPreviewUrls(top10, previewSize)

    // Build final result: best match first, then other 9
    const results = []

    if (transformed.length > 0) {
      const bm = transformed[0]
      const original = top10[0]
      const whashDist = parseInt(original.whash_distance, 10)
      const ahashDist = parseInt(original.ahash_distance, 10)
      const phashDist = parseInt(original.phash_distance, 10)
      const minDist = Math.min(whashDist, ahashDist, phashDist)
      
      results.push({
        fileId: bm.fileId,
        filename: bm.filename,
        displayName: bm.displayName,
        previewUrl: bm.previewUrl,
        whashDistance: whashDist,
        ahashDistance: ahashDist,
        phashDistance: phashDist,
        combinedDistance: minDist,
        rank: 1,
        isBestMatch: true,
      })
    }

    transformed.slice(1).forEach((row: any, index: number) => {
      const original = top10[index + 1]
      const whashDist = parseInt(original.whash_distance, 10)
      const ahashDist = parseInt(original.ahash_distance, 10)
      const phashDist = parseInt(original.phash_distance, 10)
      const minDist = Math.min(whashDist, ahashDist, phashDist)

      results.push({
        fileId: row.fileId,
        filename: row.filename,
        displayName: row.displayName,
        previewUrl: row.previewUrl,
        whashDistance: whashDist,
        ahashDistance: ahashDist,
        phashDistance: phashDist,
        combinedDistance: minDist,
        rank: index + 2,
        isBestMatch: false,
      })
    })

    console.log('[reverse-search] Returning', results.length, 'results')
    return results
  } catch (error: any) {
    console.error('[reverse-search] Error:', error)
    console.error('[reverse-search] Error stack:', error.stack)
    try { await pool.end() } catch (_) {}
    throw createError({
      statusCode: 500,
      statusMessage: 'Reverse search failed',
      data: error.message,
    })
  }
})
