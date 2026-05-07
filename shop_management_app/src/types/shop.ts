import type { Account } from './account'

export interface Shop {
  shop_id: number
  shop_name: string
  account_count?: number
  file_count?: number
}

export interface ShopFormData {
  shop_name: string
}

export interface ShopWithAccounts extends Shop {
  accounts?: Account[]
}
