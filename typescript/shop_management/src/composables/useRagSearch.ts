/**
 * Composable for RAG (Retrieval-Augmented Generation) semantic search.
 *
 * Provides natural language search over files using TF-IDF weighted embeddings.
 */

import { reactive } from 'vue'

export interface SearchResult {
  file_id: number | string
  filename: string
  similarity: number
  preview_url: string
  tags?: string
}

export interface RagSearchResponse {
  results: SearchResult[]
  query_time_ms: number
}

export interface UseRagSearchOptions {
  top_k?: number
  previewSize?: number
}

function createSearchState() {
  return reactive({
    results: [] as SearchResult[],
    isLoading: false,
    error: null as string | null,
    queryTimeMs: 0
  })
}

export function useRagSearch() {
  const state = createSearchState()
  let lastQuery = ''
  let lastOptions: UseRagSearchOptions = {}

  /**
   * Perform semantic search.
   *
   * @param query - Natural language search query
   * @param options - Search options (top_k, previewSize)
   */
  async function search(
    query: string,
    options: UseRagSearchOptions = {}
  ): Promise<RagSearchResponse> {
    lastQuery = query
    lastOptions = options

    const { top_k = 24, previewSize = 540 } = options

    state.isLoading = true
    state.error = null

    try {
      const response = await $fetch<RagSearchResponse>('/api/files/rag-search', {
        method: 'POST',
        body: {
          query,
          top_k,
          previewSize
        }
      })

      // Transform preview URLs to use the local preview proxy API
      const transformedResults = response.results.map((result: SearchResult) => ({
        ...result,
        preview_url: buildPreviewProxyUrl(result.preview_url, options.previewSize || 540)
      }))

      state.results = transformedResults
      state.queryTimeMs = response.query_time_ms
      return {
        results: transformedResults,
        query_time_ms: response.query_time_ms
      }
    } catch (err: any) {
      state.error = err.message || 'Search failed'
      state.results = []
      throw err
    } finally {
      state.isLoading = false
    }
  }

  /**
   * Clear search results.
   */
  function clearResults() {
    state.results = []
    state.error = null
    state.queryTimeMs = 0
    lastQuery = ''
    lastOptions = {}
  }

  /**
   * Retry the last search.
   */
  async function retryLastSearch() {
    if (!lastQuery) {
      throw new Error('No previous search to retry')
    }
    return search(lastQuery, lastOptions)
  }

  /**
   * Build a preview proxy URL from a raw preview_url.
   * Extracts the fileId and uses the local preview proxy API.
   */
  function buildPreviewProxyUrl(previewUrl: string, size: number): string {
    if (!previewUrl) return ''
    
    // Extract fileId from URLs like "/core/preview?fileId=8093&{prevsize}"
    const fileIdMatch = previewUrl.match(/fileId=(\d+)/)
    if (fileIdMatch) {
      return `/api/files/preview-proxy/${fileIdMatch[1]}?x=${size}&y=${size}`
    }
    
    // Fallback: return empty string if no fileId found
    return ''
  }

  return {
    results: state.results,
    isLoading: state.isLoading,
    error: state.error,
    queryTimeMs: state.queryTimeMs,
    search,
    clearResults,
    retryLastSearch
  }
}
