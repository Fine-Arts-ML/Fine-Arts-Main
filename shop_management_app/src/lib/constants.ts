export const HASH_TYPES = {
  WHASH: 'whash',
  AHASH: 'ahash',
  PHASH: 'phash',
} as const

export type HashType = typeof HASH_TYPES[keyof typeof HASH_TYPES]

export const IMAGE_RESIZE_CONFIG = {
  SMALL: { width: 220, height: 220 },
  MEDIUM: { width: 540, height: 540 },
  LARGE: { width: 1080, height: 1080 },
} as const

export const DEFAULT_BATCH_SIZE = 20
export const MAX_BATCH_SIZE = 100

export const TABS = {
  SHOPS: 'shops',
  ACCOUNTS: 'accounts',
  PERFORMANCE: 'performance',
  OVERVIEW: 'overview',
  ADD_FILES: 'add-files',
} as const
