export interface LinkedFileResult {
  fileId: number
  filename: string
  previewUrl: string | null
  displayName: string | null
  accountId: number | bigint
  accountName: string
  accountNames: string[] // All account names linked to this file in the shop
}

export interface ShopAccountWithFileCount {
  accountId: number | bigint
  accountName: string
  fileCount: number | bigint
}
