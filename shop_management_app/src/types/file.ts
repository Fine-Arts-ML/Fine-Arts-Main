export interface File {
  file_id: number
  filename: string
  display_name?: string
  account_name?: string
  preview_url?: string
  is_linked?: boolean
}

export interface FileSearchResult extends File {
  hash_match?: number
}

export interface FileFormData {
  file_id: number
  shop_id: number
  account_ids: number[]
}

export interface ImageSearchData {
  image: File | Blob
  hashType: 'whash' | 'ahash' | 'phash'
  threshold: number
}
