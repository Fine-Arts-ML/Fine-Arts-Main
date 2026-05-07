export interface LinkFileResult {
  fileId: number
  filename: string
  displayName?: string
  previewUrl: string
  whashDistance?: number
  ahashDistance?: number
  phashDistance?: number
  combinedDistance?: number
  rank?: number
}

export interface LinkFileRequest {
  fileId: number
  shopId: number
  accountId: number
}

export interface HashResult {
  whash: string
  ahash: string
  phash: string
}

export type HashMethod = 'whash' | 'ahash' | 'phash' | 'average'

export type SearchMode = 'filename' | 'reverse'
