export interface Account {
  account_id: number
  account_name: string
}

export interface AccountFormData {
  account_name: string
}

export interface ShopAccountLink {
  shop_id: number
  account_id: number
}
