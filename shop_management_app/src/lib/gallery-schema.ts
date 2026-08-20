// Gallery Schema Definitions
// This file defines the database schema for the gallery management feature
// Note: Uses oc_filecache.fileid (bigint PK) as the canonical file identifier

import { pgTable, serial, varchar, text, integer, boolean, timestamp, bigint, uniqueIndex, index, type PgTableExtraConfig } from 'drizzle-orm/pg-core'
import { userAccounts } from './auth-schema'
import { ocFilecache } from './nextcloud-schema'

// --- Global Caption Pool ---
export const captions = pgTable('bre_captions', {
  captionId: serial('caption_id').primaryKey(),
  caption: text('caption').notNull().unique(),
  createdById: integer('created_by')
    .notNull()
    .references(() => userAccounts.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
})

// Gallery Master Table
export const galleries = pgTable('bre_galleries', {
  id: serial('id').primaryKey(),
  name: varchar('name', { length: 255 }).notNull(),
  description: text('description'),
  createdById: integer('created_by').notNull().references(() => userAccounts.id),
  updatedById: integer('updated_by').references(() => userAccounts.id),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
})

// Gallery Access Table (maps guests to galleries)
export const galleryAccess = pgTable('bre_gallery_access', {
  galleryId: integer('gallery_id').notNull().references(() => galleries.id, { onDelete: 'cascade' }),
  guestUserId: integer('guest_user_id').notNull().references(() => userAccounts.id),
  grantedById: integer('granted_by').notNull().references(() => userAccounts.id),
  grantedAt: timestamp('granted_at').notNull().defaultNow(),
})

// Gallery-Image Mapping Table
// References oc_filecache.fileid (bigint PK) as the canonical file identifier
export const galleryImages = pgTable('bre_gallery_images', {
  id: serial('id').primaryKey(),
  galleryId: integer('gallery_id').notNull().references(() => galleries.id, { onDelete: 'cascade' }),
  fileId: bigint('file_id', { mode: 'number' }).notNull().references(() => ocFilecache.fileid),
  displayOrder: integer('display_order').notNull().default(0),
  addedById: integer('added_by').notNull().references(() => userAccounts.id),
  addedAt: timestamp('added_at').notNull().defaultNow(),
})

// Gallery Image Captions Table (multiple captions per image, linked to global caption pool)
export const galleryImageCaptions = pgTable('bre_gallery_image_captions', {
  id: serial('id').primaryKey(),
  galleryImageId: integer('gallery_image_id')
    .notNull()
    .references(() => galleryImages.id, { onDelete: 'cascade' }),
  captionId: integer('caption_id')
    .notNull()
    .references(() => captions.captionId, { onDelete: 'cascade' }),
  isMain: boolean('is_main').notNull().default(false),
  createdById: integer('created_by')
    .notNull()
    .references(() => userAccounts.id),
  createdAt: timestamp('created_at').notNull().defaultNow(),
}, (table) => ({
  indexes: {
    uqGalleryImageCaption: uniqueIndex('uq_gallery_image_caption').on(table.galleryImageId, table.captionId),
    galleryImageIdIdx: index('gallery_image_captions_gallery_image_id_idx').on(table.galleryImageId),
    captionIdIdx: index('gallery_image_captions_caption_id_idx').on(table.captionId),
  },
}))

// Import oc_filecache from nextcloud-schema (needed for galleryImages reference)
// Already imported above

// Type definitions
export type Caption = typeof captions.$inferSelect
export type NewCaption = typeof captions.$inferInsert
export type Gallery = typeof galleries.$inferSelect
export type NewGallery = typeof galleries.$inferInsert
export type GalleryAccess = typeof galleryAccess.$inferSelect
export type NewGalleryAccess = typeof galleryAccess.$inferInsert
export type GalleryImage = typeof galleryImages.$inferSelect
export type NewGalleryImage = typeof galleryImages.$inferInsert
export type GalleryImageCaption = typeof galleryImageCaptions.$inferSelect
export type NewGalleryImageCaption = typeof galleryImageCaptions.$inferInsert
