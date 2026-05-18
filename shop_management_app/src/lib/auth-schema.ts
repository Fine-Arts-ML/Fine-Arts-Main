// Auth Schema Definitions
// This file defines the database schema for user authentication and sessions
// Note: Indexes are created via SQL migration (0001_add_auth_tables.sql)

import { pgTable, serial, varchar, boolean, timestamp, integer, jsonb, text } from 'drizzle-orm/pg-core'

// User Accounts table: Maps Nextcloud users to app roles
export const userAccounts = pgTable('bre_user_accounts', {
  id: serial('id').primaryKey(),
  nextcloudUid: varchar('nextcloud_uid').notNull().unique(),
  role: varchar('role').notNull().default('user'), // 'guest' | 'user' | 'admin'
  allowedGalleryIds: jsonb('allowed_gallery_ids').default([]),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
})

// Sessions table: Server-side session storage
export const sessions = pgTable('bre_sessions', {
  id: varchar('id', { length: 128 }).primaryKey(),
  userId: integer('user_id').references(() => userAccounts.id),
  sessionData: jsonb('session_data').notNull().default({}),
  expiresAt: timestamp('expires_at').notNull(),
  createdAt: timestamp('created_at').notNull().defaultNow(),
})

// Nextcloud Users table (read-only reference)
export const ocUsers = pgTable('oc_users', {
  uid: varchar('uid').primaryKey(),
  displayname: varchar('displayname'),
  password: varchar('password').notNull(),
  uidLower: varchar('uid_lower'),
})

// Nextcloud Groups table (read-only reference)
export const ocGroups = pgTable('oc_groups', {
  gid: varchar('gid', { length: 64 }).primaryKey(),
  displayname: varchar('displayname', { length: 255 }).notNull(),
})

// Nextcloud Group Users mapping (read-only reference)
export const ocGroupUser = pgTable('oc_group_user', {
  gid: varchar('gid', { length: 64 }).notNull(),
  uid: varchar('uid', { length: 64 }).notNull(),
})

// Nextcloud Accounts table (read-only reference)
export const ocAccounts = pgTable('oc_accounts', {
  uid: varchar('uid', { length: 64 }).primaryKey(),
  data: text('data').notNull(),
})

// Type definitions
export type UserAccount = typeof userAccounts.$inferSelect
export type NewUserAccount = typeof userAccounts.$inferInsert
export type Session = typeof sessions.$inferSelect
export type NewSession = typeof sessions.$inferInsert
export type NextcloudUser = typeof ocUsers.$inferSelect
export type NextcloudGroup = typeof ocGroups.$inferSelect
export type NextcloudGroupUser = typeof ocGroupUser.$inferSelect
export type NextcloudAccount = typeof ocAccounts.$inferSelect
