// Drizzle ORM Schema Definitions
// This file defines the database schema for the Shop Management application

import { pgTable, serial, text, integer, bigint } from 'drizzle-orm/pg-core'

// Shop table
export const shops = pgTable('bre_shops', {
  shopId: bigint('shop_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  shopName: text('shop_name').notNull(),
})

// Account table
export const accounts = pgTable('bre_shop_account', {
  accountId: bigint('account_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  accountName: text('account_name').notNull(),
})

// Shop-Account relationship table
export const shopAccountMatrix = pgTable('bre_shop_account_matrix', {
  shopId: bigint('shop_id', { mode: 'bigint' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'bigint' }).references(() => accounts.accountId),
})

// Account-File index table
export const accountIndex = pgTable('bre_account_index', {
  fileId: integer('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
})

// Shop-File index table
export const shopsIndex = pgTable('bre_shops_index', {
  id: text('id').primaryKey(),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
})

// Advance index (file metadata)
export const advanceIndex = pgTable('bre_advance_index', {
  fileId: integer('fileid').primaryKey().generatedAlwaysAsIdentity(),
  name: text('name').notNull(),
  previewUrl: text('preview_url'),
})

// Display name table
export const displayName = pgTable('bre_display_names', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).primaryKey(),
  displayName: text('display_name').notNull(),
})

// Display name relationship table (maps display names to shop/account/file)
export const displayNameMatrix = pgTable('bre_display_name_index', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).references(() => displayName.displayNameId),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
  fileId: text('file_id'),
})

// File-Junction table (triadic: shop + file + account)
// This is the source of truth for all shop/account/file relationships
// Note: Uses raw SQL for queries since Drizzle doesn't handle composite PKs well
export const fileJunction = pgTable('bre_file_junction', {
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  fileId: text('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
})

// RAG Model Settings table (stores user preferences for RAG search)
export const ragModelSettings = pgTable('rag_model_settings', {
  id: serial('id').primaryKey(),
  key: text('key').notNull().unique(), // e.g., 'current_model', 'max_cached_models'
  value: text('value').notNull(), // e.g., 'qwen3-0.6b', '1'
  description: text('description'),
  updatedAt: text('updated_at'),
})
