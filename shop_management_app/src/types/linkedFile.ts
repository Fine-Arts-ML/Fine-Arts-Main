export interface LinkedFileResult {
  fileId: number
  filename: string
  previewUrl: string | null
  displayName: string | null
  allDisplayNames: string[] // All display names linked to this file in the shop
  published: boolean
  accountId: number | bigint
  accountName: string
  accountNames: string[] // All account names linked to this file in the shop
}

export interface ShopAccountWithFileCount {
  accountId: number | bigint
  accountName: string
  fileCount: number | bigint
}
