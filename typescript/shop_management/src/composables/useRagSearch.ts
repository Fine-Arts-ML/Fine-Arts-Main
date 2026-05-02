/**
 * Composable for RAG (Retrieval-Augmented Generation) semantic search.
 *
 * Provides natural language search over files using TF-IDF weighted embeddings.
 * Supports infinite scroll pagination with similarity threshold filtering.
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
  has_more: boolean
  total_matching: number
  min_similarity: number
}

export interface UseRagSearchOptions {
  top_k?: number
  previewSize?: number
  min_similarity?: number
}

function createSearchState() {
  return reactive({
    results: [] as SearchResult[],
    isLoading: false,
    isLoadingMore: false,
    error: null as string | null,
    queryTimeMs: 0,
    hasMore: false,
    totalMatching: 0,
    minSimilarity: 0.25
  })
}

export function useRagSearch() {
  const state = createSearchState()
  let lastQuery = ''
  let lastOptions: UseRagSearchOptions = {}

  /**
   * Perform semantic search (first page).
   *
   * @param query - Natural language search query
   * @param options - Search options (top_k, previewSize, min_similarity)
   */
  async function search(
    query: string,
    options: UseRagSearchOptions = {}
  ): Promise<RagSearchResponse> {
    lastQuery = query
    lastOptions = options

    const { top_k = 24, previewSize = 540, min_similarity = 0.25 } = options

    state.isLoading = true
    state.isLoadingMore = false
    state.error = null

    try {
      const response = await $fetch<RagSearchResponse>('/api/files/rag-search', {
        method: 'POST',
        body: {
          query,
          top_k,
          previewSize,
          min_similarity,
          offset: 0
        }
      })

      // Transform preview URLs to use the local preview proxy API
      const transformedResults = response.results.map((result: SearchResult) => ({
        ...result,
        preview_url: buildPreviewProxyUrl(result.preview_url, options.previewSize || 540)
      }))

      state.results = transformedResults
      state.queryTimeMs = response.query_time_ms
      state.hasMore = response.has_more ?? false
      state.totalMatching = response.total_matching ?? 0
      state.minSimilarity = response.min_similarity ?? min_similarity
      return {
        results: transformedResults,
        query_time_ms: response.query_time_ms,
        has_more: response.has_more ?? false,
        total_matching: response.total_matching ?? 0,
        min_similarity: response.min_similarity ?? min_similarity
      }
    } catch (err: any) {
      state.error = err.message || 'Search failed'
      state.results = []
      state.hasMore = false
      state.totalMatching = 0
      throw err
    } finally {
      state.isLoading = false
    }
  }

  /**
   * Load more results (pagination for infinite scroll).
   *
   * @param options - Search options (top_k, previewSize, min_similarity)
   * @returns Promise resolving to the RagSearchResponse with appended results
   */
  async function loadMore(
    options: UseRagSearchOptions = {}
  ): Promise<RagSearchResponse> {
    const { top_k = 24, previewSize = 540, min_similarity = 0.25 } = options

    if (!lastQuery) {
      throw new Error('No previous search to load more. Call search() first.')
    }

    state.isLoadingMore = true
    state.error = null

    try {
      const currentOffset = state.results.length
      const response = await $fetch<RagSearchResponse>('/api/files/rag-search', {
        method: 'POST',
        body: {
          query: lastQuery,
          top_k,
          previewSize,
          min_similarity: min_similarity || state.minSimilarity,
          offset: currentOffset
        }
      })

      // Transform preview URLs to use the local preview proxy API
      const transformedResults = response.results.map((result: SearchResult) => ({
        ...result,
        preview_url: buildPreviewProxyUrl(result.preview_url, options.previewSize || 540)
      }))

      // Append to existing results
      state.results = [...state.results, ...transformedResults]
      state.hasMore = response.has_more ?? false
      state.totalMatching = response.total_matching ?? state.totalMatching
      state.minSimilarity = response.min_similarity ?? state.minSimilarity

      return {
        results: transformedResults,
        query_time_ms: response.query_time_ms,
        has_more: response.has_more ?? false,
        total_matching: response.total_matching ?? state.totalMatching,
        min_similarity: response.min_similarity ?? state.minSimilarity
      }
    } catch (err: any) {
      state.error = err.message || 'Failed to load more results'
      throw err
    } finally {
      state.isLoadingMore = false
    }
  }

  /**
   * Clear search results.
   */
  function clearResults() {
    state.results = []
    state.isLoading = false
    state.isLoadingMore = false
    state.error = null
    state.queryTimeMs = 0
    state.hasMore = false
    state.totalMatching = 0
    state.minSimilarity = 0.25
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
    isLoadingMore: state.isLoadingMore,
    error: state.error,
    queryTimeMs: state.queryTimeMs,
    hasMore: state.hasMore,
    totalMatching: state.totalMatching,
    minSimilarity: state.minSimilarity,
    search,
    loadMore,
    clearResults,
    retryLastSearch
  }
}
