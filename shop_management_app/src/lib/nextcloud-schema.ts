// Nextcloud Schema Definitions (Read-Only Reference)
// This file defines the database schema for Nextcloud tables we interact with
// Note: Indexes are managed by Nextcloud; we only read from these tables

import { pgTable, serial, varchar, bigint, boolean, timestamp, integer, text } from 'drizzle-orm/pg-core'

// Nextcloud File Cache table - stores file metadata
// Key columns: fileid, parent, name, size, mime_type, mtime, path
export const ocFilecache = pgTable('oc_filecache', {
  fileid: bigint('fileid', { mode: 'number' }).primaryKey(),
  storage: varchar('storage', { length: 255 }),
  path: varchar('path', { length: 255 }),
  pathHash: varchar('path_hash', { length: 255 }),
  parent: bigint('parent', { mode: 'number' }),
  name: varchar('name', { length: 255 }),
  mimetype: bigint('mimetype', { mode: 'number' }),
  storage_mtime: varchar('storage_mtime', { length: 255 }),
  encrypted: integer('encrypted'),
  encryption_version: integer('encryption_version'),
  etag: varchar('etag', { length: 255 }),
  size: bigint('size', { mode: 'number' }),
  mtime: bigint('mtime', { mode: 'number' }),
  storage_id: varchar('storage_id', { length: 255 }),
  metadata_id: bigint('metadata_id', { mode: 'number' }),
  metadata_etag: varchar('metadata_etag', { length: 255 }),
  metadata_created_at: varchar('metadata_created_at', { length: 255 }),
  metadata_tags: varchar('metadata_tags', { length: 255 }),
  metadata_altitudes: varchar('metadata_altitudes', { length: 255 }),
  metadata_latitude: varchar('metadata_latitude', { length: 255 }),
  metadata_longitudes: varchar('metadata_longitudes', { length: 255 }),
  metadata_description: varchar('metadata_description', { length: 255 }),
  // Computed columns (not in DB but returned by queries)
  isDirectory: boolean('is_directory').default(false),
})

// Nextcloud System Tags table - stores tag definitions
export const ocSystemtag = pgTable('oc_systemtag', {
  id: bigint('id', { mode: 'number' }).primaryKey(),
  name: varchar('name', { length: 255 }).notNull(),
  visibility: integer('visibility').notNull(),
  editable: integer('editable').notNull(),
  etag: varchar('etag', { length: 255 }),
  color: varchar('color', { length: 255 }),
})

// Nextcloud System Tags Object Mapping table - stores tag-to-file mappings
export const ocSystemtagObjectMapping = pgTable('oc_systemtag_object_mapping', {
  objectid: varchar('objectid', { length: 255 }).notNull(),
  objecttype: varchar('objecttype', { length: 255 }).notNull(),
  systemtagid: bigint('systemtagid', { mode: 'number' }).notNull(),
})

// Nextcloud Mimetype table - maps mimetype IDs to names
export const ocMimetype = pgTable('oc_mimetype', {
  id: bigint('id', { mode: 'number' }).primaryKey(),
  mimetype: varchar('mimetype', { length: 255 }),
})

// Application-managed: Tag Cache - cached tag lookup for faster queries
export const breTagCache = pgTable('bre_tag_cache', {
  id: bigint('id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  tagName: varchar('tag_name', { length: 255 }).notNull().unique(),
  ocTagId: bigint('oc_tag_id', { mode: 'number' }).notNull(),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
})

// Application-managed: Tag Mapping Index - application-level tag-to-file mapping
export const breTagMappingIndex = pgTable('bre_tag_mapping_index', {
  id: bigint('id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  fileId: varchar('file_id', { length: 255 }).notNull(),
  tagName: varchar('tag_name', { length: 255 }).notNull(),
  ocTagId: bigint('oc_tag_id', { mode: 'number' }).notNull(),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
})

// Application-managed: File Tracker - track file existence
export const breFileTracker = pgTable('bre_file_tracker', {
  id: bigint('id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  fileId: varchar('file_id', { length: 255 }).notNull().unique(),
  fileName: varchar('file_name', { length: 500 }).notNull(),
  filePath: varchar('file_path', { length: 1000 }).notNull(),
  isPresent: boolean('is_present').default(true),
  lastChecked: timestamp('last_checked').defaultNow(),
  createdAt: timestamp('created_at').defaultNow(),
})

// =============================================================================
// Staging Tables: Session-based tag and description staging
// =============================================================================

// Application-managed: Staging Tags - stores unique staged tag values per session
export const breTagsStaging = pgTable('bre_tags_staging', {
  id: serial('id').primaryKey(),
  sessionId: varchar('session_id', { length: 128 }).notNull(),
  name: varchar('name', { length: 255 }).notNull(),
  visibility: integer('visibility').notNull().default(1),
  editable: integer('editable').notNull().default(1),
  createdAt: timestamp('created_at').defaultNow(),
})

// Application-managed: Staging Tag Map - maps staged tags to file IDs per session
export const breTagMapStaging = pgTable('bre_tag_map_staging', {
  id: serial('id').primaryKey(),
  sessionId: varchar('session_id', { length: 128 }).notNull(),
  tagId: integer('tag_id').notNull().references(() => breTagsStaging.id, { onDelete: 'cascade' }),
  fileId: varchar('file_id', { length: 255 }).notNull(),
  createdAt: timestamp('created_at').defaultNow(),
})

// Application-managed: Staging Descriptions - staged descriptions per session
export const breDescriptionsStaging = pgTable('bre_descriptions_staging', {
  id: serial('id').primaryKey(),
  sessionId: varchar('session_id', { length: 128 }).notNull(),
  fileId: varchar('file_id', { length: 255 }).notNull(),
  description: text('description').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
})

// Application-managed: Descriptions - production descriptions (max 3 per file with pinning)
export const breDescriptions = pgTable('bre_descriptions', {
  id: serial('id').primaryKey(),
  fileId: varchar('file_id', { length: 255 }).notNull(),
  description: text('description').notNull(),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
  pinned: boolean('pinned').notNull().default(false),
})

// Application-managed: Index Configuration - stores re-index settings
export const breIndexConfig = pgTable('bre_index_config', {
  id: bigint('id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  key: varchar('key', { length: 255 }).notNull().unique(),
  value: text('value'),
  description: text('description'),
  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
})

// Type definitions
export type OcFilecache = typeof ocFilecache.$inferSelect
export type NewOcFilecache = typeof ocFilecache.$inferInsert
export type OcSystemtag = typeof ocSystemtag.$inferSelect
export type NewOcSystemtag = typeof ocSystemtag.$inferInsert
export type OcSystemtagObjectMapping = typeof ocSystemtagObjectMapping.$inferSelect
export type NewOcSystemtagObjectMapping = typeof ocSystemtagObjectMapping.$inferInsert
export type BreTagCache = typeof breTagCache.$inferSelect
export type NewBreTagCache = typeof breTagCache.$inferInsert
export type BreTagMappingIndex = typeof breTagMappingIndex.$inferSelect
export type NewBreTagMappingIndex = typeof breTagMappingIndex.$inferInsert
export type BreFileTracker = typeof breFileTracker.$inferSelect
export type NewBreFileTracker = typeof breFileTracker.$inferInsert
// Staging table types
export type BreTagsStaging = typeof breTagsStaging.$inferSelect
export type NewBreTagsStaging = typeof breTagsStaging.$inferInsert
export type BreTagMapStaging = typeof breTagMapStaging.$inferSelect
export type NewBreTagMapStaging = typeof breTagMapStaging.$inferInsert
export type BreDescriptionsStaging = typeof breDescriptionsStaging.$inferSelect
export type NewBreDescriptionsStaging = typeof breDescriptionsStaging.$inferInsert
export type BreDescriptions = typeof breDescriptions.$inferSelect
export type NewBreDescriptions = typeof breDescriptions.$inferInsert
export type BreIndexConfig = typeof breIndexConfig.$inferSelect
export type NewBreIndexConfig = typeof breIndexConfig.$inferInsert
