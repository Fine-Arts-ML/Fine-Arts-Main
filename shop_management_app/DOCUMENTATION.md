# Shop Management Application - Technical Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Configuration](#configuration)
6. [Database Schema](#database-schema)
7. [API Reference](#api-reference)
8. [Composables](#composables)
9. [Pages](#pages)
10. [Layouts](#layouts)
11. [Types](#types)
12. [Utilities](#utilities)
13. [Styling](#styling)
14. [Environment Variables](#environment-variables)
15. [Python Integration](#python-integration)
16. [RAG Search](#rag-search)
17. [Development](#development)
18. [Deployment](#deployment)
19. [File Index](#file-index)

---

## Overview

The Shop Management Application is a full-stack web application built with Nuxt 3 for managing art shops, accounts, and their linked files. It provides CRUD operations for shops and accounts, file management with search capabilities, and integrates with Nextcloud for file previews and Python-based perceptual hashing for reverse image search.

### Key Features

- **Shop Management**: Create, read, update, and delete shops
- **Account Management**: Create, read, and delete accounts
- **Shop-Account Linking**: Many-to-many relationship management between shops and accounts via `bre_shop_account_matrix`
- **File Management**: Link files to shops and accounts with preview support
- **File Search**: Text search by filename and display name using `ILIKE` queries
- **Linked Files Browser**: Hierarchical browsing of files by shop and account with pagination
- **File Linking/Unlinking**: Link files to shops/accounts via `bre_file_junction` triadic relationship table
- **Reverse Image Search**: Perceptual hash-based image similarity search using Python's `imagehash` library
- **Theme Support**: Light and dark mode with system preference detection and localStorage persistence
- **Nextcloud Integration**: Fetch preview images from Nextcloud servers via authenticated proxy

---

## Architecture

The application follows the Nuxt 3 full-stack architecture with:

- **Frontend**: Vue 3 Composition API with TypeScript
- **Backend**: Nuxt Server Routes (API endpoints)
- **Database**: PostgreSQL with Drizzle ORM (for structured queries) and raw `pg` pool (for complex queries)
- **State Management**: Pinia stores and Vue composables
- **Server State**: TanStack Query for server state management
- **Python Integration**: Subprocess-based communication for perceptual hash calculation

### Data Flow

```
User Action -> Vue Component -> Composable -> API Route -> Database
                                      <-             <-
```

1. User interacts with a Vue page component
2. Page calls a composable function
3. Composable makes `$fetch` calls to server API routes
4. API routes query the PostgreSQL database via Drizzle ORM or raw `pg` pool
5. Results flow back through the composable to the component

### Architecture Notes

- **Dual Database Access**: Some API routes use Drizzle ORM (`~/lib/db`) for type-safe queries, while others use raw `pg` pool for complex SQL (e.g., `linked-files-search`, `reverse-search`, `search-by-name`). This is because the underlying database schema uses non-standard table/column names (`bre_*` prefix) that are not fully modeled in Drizzle.
- **SSR-Compatible Theme**: Theme is applied via an inline synchronous script in `<head>` (before Vue renders) to prevent FOUC (Flash of Unstyled Content). Vue syncs with the DOM state on mount.

---

## Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | Nuxt 3 | 3.13+ |
| Language | TypeScript | 5.5+ |
| UI Framework | Vue 3 | 3.4+ |
| CSS Framework | Tailwind CSS | 3.4+ |
| UI Components | Radix Vue | 1.9+ |
| State Management | Pinia | 2.1+ |
| Server State | TanStack Query | 5.51+ |
| Database ORM | Drizzle ORM | 0.33+ |
| Database Client | PostgreSQL (pg) | 8.20+ |
| Database | PostgreSQL | 16+ |
| Form Validation | VeeValidate + Zod | 4.13+ / 3.23+ |
| Table Management | TanStack Table | 8.17+ |
| Icon Library | Lucide Vue Next | 0.400+ |
| Date Handling | date-fns | 3.6+ |
| Image Processing | JIMP | 0.22+ |

---

## Project Structure

```
typescript/shop_management/
├── src/
│   ├── app.config.ts          # App-wide configuration (unopinionated defaults)
│   ├── app.vue                # Root application component
│   ├── env.d.ts               # Environment type declarations
│   ├── assets/
│   │   └── css/
│   │       ├── global.css     # Global styles with CSS variables for theming
│   │       └── tree-view.css  # Tree view visualization styles (NOTE: file may be missing)
│   ├── composables/           # Vue composables (reactive logic)
│   │   ├── useLinkedFiles.ts  # Linked files browsing logic (Shop -> Account -> Files)
│   │   ├── useLinkFiles.ts    # File linking logic (search, reverse search, link)
│   │   ├── useShops.ts        # Shop management logic
│   │   └── useTheme.ts        # Theme toggle logic
│   ├── layouts/
│   │   └── default.vue        # Default layout with collapsible sidebar
│   ├── lib/
│   │   ├── constants.ts       # Application constants (hash types, image sizes, tabs)
│   │   ├── db.ts              # Database connection utility (Drizzle ORM + pg Pool)
│   │   ├── schema.ts          # Drizzle ORM schema definitions
│   │   └── utils.ts           # Helper utilities (cn, formatFileSize, transformPreviewUrl)
│   ├── pages/                 # File-based routing
│   │   ├── index.vue          # Home page (redirects to /shops)
│   │   ├── shops.vue          # Shop & Account management
│   │   ├── files.vue          # Linked files browser
│   │   ├── link-files.vue     # Search and link files to shops/accounts
│   │   ├── browse.vue         # File browsing with tabs (skeleton)
│   │   ├── performance.vue    # Performance page (skeleton)
│   │   └── settings.vue       # Application settings
│   ├── plugins/
│   │   └── theme.ts           # Theme plugin for initial sync
│   ├── server/
│   │   ├── api/               # Nuxt server API routes
│   │   │   ├── accounts/
│   │   │   │   ├── index.get.ts        # List all accounts with shop counts
│   │   │   │   ├── index.post.ts       # Create new account
│   │   │   │   └── [id].delete.ts      # Delete account
│   │   │   ├── files/
│   │   │   │   ├── index.get.ts        # List all files with shop/account info
│   │   │   │   ├── index.post.ts       # Create new file entry
│   │   │   │   ├── search-by-name.get.ts    # Search files by name/display name
│   │   │   │   ├── link-to-shop-account.post.ts # Link file to shop and account
│   │   │   │   ├── unlink.post.ts             # Unlink file from shop/account
│   │   │   │   ├── reverse-search.post.ts     # Reverse image search
│   │   │   │   ├── [fileId]/
│   │   │   │   │   └── tags.get.ts         # Get tags for a file
│   │   │   │   └── preview-proxy/
│   │   │   │       └── [fileId].get.ts     # Proxy for Nextcloud previews
│   │   │   └── shops/
│   │   │       ├── index.get.ts          # List all shops with counts
│   │   │       ├── index.post.ts         # Create new shop
│   │   │       ├── [id].delete.ts        # Delete shop
│   │   │       ├── [id].put.ts           # Update shop
│   │   │       └── [id]/
│   │   │           ├── accounts.get.ts           # Get shop accounts
│   │   │           ├── accounts.post.ts          # Link account to shop
│   │   │           ├── accounts.delete.ts        # Unlink account from shop
│   │   │           ├── accounts-with-files.get.ts # Accounts with file counts (shop-filtered)
│   │   │           ├── files.get.ts              # Get shop files (optionally filtered by account)
│   │   │           ├── files.search.get.ts       # Search shop files by name/display name
│   │   │           ├── all-files.get.ts          # Get all files for shop across all accounts
│   │   │           └── linked-files-search.get.ts # Advanced linked file search
│   │   └── utils/
│   │       └── preview.ts          # Preview URL transformation utilities
│   ├── types/
│   │   ├── index.ts           # Type exports
│   │   ├── shop.ts            # Shop-related types
│   │   ├── account.ts         # Account-related types
│   │   ├── file.ts            # File-related types
│   │   ├── linkedFile.ts      # Linked file types
│   │   └── linkFiles.ts       # File linking types
│   ├── composables/           # Vue composables (reactive logic)
│   │   ├── useLinkedFiles.ts  # Linked files browsing logic (Shop -> Account -> Files)
│   │   ├── useLinkFiles.ts    # File linking logic (search, reverse search, link)
│   │   ├── useRagSearch.ts    # RAG semantic search composable
│   │   ├── useRAGSettings.ts  # RAG settings management composable
│   │   ├── useShops.ts        # Shop management logic
│   │   └── useTheme.ts        # Theme toggle logic
│   ├── py-code/
│   │   ├── hash_helper.py     # Python script for perceptual hash calculation
│   │   └── rag_search/        # Python RAG Search service (FastAPI)
│   │       ├── main.py        # FastAPI application with API endpoints
│   │       ├── search.py      # Core search logic using TF-IDF weighted embeddings
│   │       ├── database.py    # Database connection and query handler
│   │       ├── model_loader.py # Embedding model loading and caching
│   │       ├── config.py      # RAG configuration
│   │       └── tfidf_index.py # TF-IDF vectorization and index persistence
├── .env.example               # Environment variables template
├── docker-compose.yml         # Docker Compose for development
├── Dockerfile                 # Production Docker image
├── Dockerfile.dev             # Development Docker image
├── drizzle.config.ts          # Drizzle ORM configuration
├── nuxt.config.ts             # Nuxt configuration
├── package.json               # Dependencies and scripts
├── tailwind.config.ts         # Tailwind CSS configuration
├── tsconfig.json              # TypeScript configuration
└── DOCUMENTATION.md           # This file
```

---

## Configuration

### Nuxt Configuration ([`nuxt.config.ts`](src/nuxt.config.ts))

```typescript
{
  srcDir: 'src/',              // Source files root
  serverDir: 'src/server/',    // Server files root
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt'],
  css: ['~/assets/css/global.css'],
  devServer: { port: 3000 },
  compatibilityVersion: 4,
  routeRules: { '/': { prerender: true } },
  runtimeConfig: {
    db: {
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    },
    nextcloud: {
      host: process.env.NC_HOST || 'localhost',
      user: process.env.NC_ACC || '',
      password: process.env.NC_PASS || '',
    },
  },
  app: {
    head: {
      script: [{
        innerHTML: '(function(){try{var t=localStorage.getItem("theme")||"light";document.documentElement.classList.toggle("dark",t==="dark");document.documentElement.setAttribute("data-theme",t)}catch(e){}})();',
        tagPriority: 'high',
      }],
    },
  },
}
```

**Runtime Config (Server-side):**
- `config.db.host`, `config.db.port`, `config.db.database`, `config.db.user`, `config.db.password` - PostgreSQL connection
- `config.nextcloud.host`, `config.nextcloud.user`, `config.nextcloud.password` - Nextcloud connection

**Client-side Environment Access:**
- `import.meta.env.NUXT_NC_HOST` - Nextcloud host for preview URLs

### Drizzle Configuration ([`drizzle.config.ts`](drizzle.config.ts))

```typescript
{
  dialect: 'postgresql',
  schema: './src/lib/schema.ts',
  dbCredentials: {
    host: process.env.DB_HOST || 'localhost',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'postgres',
    database: process.env.DB_NAME || 'shop_management',
    port: Number(process.env.DB_PORT) || 5432,
    ssl: false,
  },
  strict: true,
  verbose: true,
}
```

### TypeScript Configuration ([`tsconfig.json`](tsconfig.json))

```json
{
  "extends": "./.nuxt/tsconfig.json",
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": {
      "~/*": ["./src/*"],
      "@/*": ["./src/*"]
    }
  }
}
```

---

## Database Schema

The application uses PostgreSQL with the following tables. The schema uses a `bre_` prefix for all table names, indicating integration with an existing database system.

### Table Overview

| Table Name | Drizzle Export | Purpose |
|------------|----------------|---------|
| `bre_shops` | [`shops`](src/lib/schema.ts:7) | Shop information |
| `bre_shop_account` | [`accounts`](src/lib/schema.ts:13) | Account information |
| `bre_shop_account_matrix` | [`shopAccountMatrix`](src/lib/schema.ts:19) | Many-to-many shop-account relationships |
| `bre_account_index` | [`accountIndex`](src/lib/schema.ts:25) | File-to-account links |
| `bre_shops_index` | [`shopsIndex`](src/lib/schema.ts:31) | File-to-shop links |
| `bre_advance_index` | [`advanceIndex`](src/lib/schema.ts:37) | File metadata (name, preview URL) |
| `bre_display_names` | [`displayName`](src/lib/schema.ts:44) | Tag/display name definitions |
| `bre_display_name_index` | [`displayNameMatrix`](src/lib/schema.ts:50) | Tag-to-entity relationships |
| `bre_file_junction` | [`fileJunction`](src/lib/schema.ts:60) | Triadic shop-file-account relationships (source of truth) |
| `bre_hashes` | *(not in Drizzle schema)* | Perceptual hash values for reverse search |

### Schema Definitions

#### Shops Table (`bre_shops`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `shop_id` | `shopId` | `BIGINT` | PRIMARY KEY, `generatedByDefaultAsIdentity()` |
| `shop_name` | `shopName` | `TEXT` | NOT NULL |

**Drizzle Definition:**
```typescript
export const shops = pgTable('bre_shops', {
  shopId: bigint('shop_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  shopName: text('shop_name').notNull(),
})
```

#### Accounts Table (`bre_shop_account`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `account_id` | `accountId` | `BIGINT` | PRIMARY KEY, `generatedByDefaultAsIdentity()` |
| `account_name` | `accountName` | `TEXT` | NOT NULL |

**Drizzle Definition:**
```typescript
export const accounts = pgTable('bre_shop_account', {
  accountId: bigint('account_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  accountName: text('account_name').notNull(),
})
```

#### Shop-Account Matrix (`bre_shop_account_matrix`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `shop_id` | `shopId` | `BIGINT` | FOREIGN KEY -> `bre_shops.shop_id` |
| `account_id` | `accountId` | `BIGINT` | FOREIGN KEY -> `bre_shop_account.account_id` |

**Drizzle Definition:**
```typescript
export const shopAccountMatrix = pgTable('bre_shop_account_matrix', {
  shopId: bigint('shop_id', { mode: 'bigint' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'bigint' }).references(() => accounts.accountId),
})
```

#### Account Index (`bre_account_index`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `file_id` | `fileId` | `INTEGER` | NOT NULL |
| `account_id` | `accountId` | `BIGINT` | FOREIGN KEY -> `bre_shop_account.account_id` |

**Drizzle Definition:**
```typescript
export const accountIndex = pgTable('bre_account_index', {
  fileId: integer('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
})
```

#### Shops Index (`bre_shops_index`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `id` | `id` | `TEXT` | PRIMARY KEY (stores file ID as string) |
| `shop_id` | `shopId` | `BIGINT` | FOREIGN KEY -> `bre_shops.shop_id` |

**Drizzle Definition:**
```typescript
export const shopsIndex = pgTable('bre_shops_index', {
  id: text('id').primaryKey(),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
})
```

#### Advance Index (`bre_advance_index`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `fileid` | `fileId` | `INTEGER` | PRIMARY KEY, `generatedAlwaysAsIdentity()` |
| `name` | `name` | `TEXT` | NOT NULL |
| `preview_url` | `previewUrl` | `TEXT` | Nullable (contains Nextcloud preview path with `{prevsize}` placeholder) |

**Drizzle Definition:**
```typescript
export const advanceIndex = pgTable('bre_advance_index', {
  fileId: integer('fileid').primaryKey().generatedAlwaysAsIdentity(),
  name: text('name').notNull(),
  previewUrl: text('preview_url'),
})
```

#### Display Names (`bre_display_names`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `display_name_id` | `displayNameId` | `BIGINT` | PRIMARY KEY |
| `display_name` | `displayName` | `TEXT` | NOT NULL |

**Drizzle Definition:**
```typescript
export const displayName = pgTable('bre_display_names', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).primaryKey(),
  displayName: text('display_name').notNull(),
})
```

#### Display Name Matrix (`bre_display_name_index`)

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `display_name_id` | `displayNameId` | `BIGINT` | FOREIGN KEY -> `bre_display_names.display_name_id` |
| `shop_id` | `shopId` | `BIGINT` | FOREIGN KEY -> `bre_shops.shop_id` |
| `account_id` | `accountId` | `BIGINT` | FOREIGN KEY -> `bre_shop_account.account_id` |
| `file_id` | `fileId` | `TEXT` | Nullable (stores file ID as string) |

**Drizzle Definition:**
```typescript
export const displayNameMatrix = pgTable('bre_display_name_index', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).references(() => displayName.displayNameId),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
  fileId: text('file_id'),
})
```

#### File-Junction Table (`bre_file_junction`)

The central triadic relationship table that stores all shop-file-account relationships. This is the **source of truth** for all file linking operations, replacing the older separate index tables (`bre_account_index`, `bre_shops_index`) for query operations.

| Column | Drizzle Field | Type | Constraints |
|--------|---------------|------|-------------|
| `shop_id` | `shopId` | `BIGINT` | FOREIGN KEY -> `bre_shops.shop_id` |
| `file_id` | `fileId` | `TEXT` | NOT NULL |
| `account_id` | `accountId` | `BIGINT` | FOREIGN KEY -> `bre_shop_account.account_id` |

**Drizzle Definition:**
```typescript
export const fileJunction = pgTable('bre_file_junction', {
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  fileId: text('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
})
```

**Usage Notes:**
- All file linking operations (`link-to-shop-account`, `unlink`) use this table
- The `linked-files-search` endpoint queries this table instead of the old index tables
- ON CONFLICT DO NOTHING prevents duplicate entries during linking
- Composite relationship: a file can be linked to the same shop multiple times via different accounts

---

#### Hashes Table (`bre_hashes`) - NOT in Drizzle Schema

This table is used by the reverse image search feature but is not defined in the Drizzle schema. It is queried directly via raw SQL.

| Column | Type | Purpose |
|--------|------|---------|
| `id` | TEXT | File ID (matches `bre_advance_index.fileid` as string) |
| `w_hash` | TEXT | Wavelet hash value |
| `a_hash` | TEXT | Average hash value |
| `p_hash` | TEXT | Perceptual hash value |

---

## API Reference

### Shops API

#### GET `/api/shops`

List all shops with account and file counts.

**Database Queries:**

1. **Fetch shops:**
```sql
SELECT shop_id, shop_name FROM bre_shops ORDER BY shop_name ASC
```

2. **Fetch account counts per shop:**
```sql
SELECT shop_id, COUNT(account_id) AS account_count
FROM bre_shop_account_matrix
GROUP BY shop_id
```

3. **Fetch file counts per shop:**
```sql
SELECT shop_id, COUNT(id) AS file_count
FROM bre_shops_index
GROUP BY shop_id
```

**Response:**
```json
[
  {
    "shop_id": 1,
    "shop_name": "Gallery A",
    "account_count": 5,
    "file_count": 150
  }
]
```

**Implementation:** [`src/server/api/shops/index.get.ts`](src/server/api/shops/index.get.ts)

---

#### POST `/api/shops`

Create a new shop with an explicit ID.

**Request Body:**
```json
{
  "shopName": "New Shop"
}
```

**Database Query:**
```sql
-- Get next available ID
SELECT MAX(shop_id) AS max FROM bre_shops

-- Insert with explicit ID
INSERT INTO bre_shops (shop_id, shop_name) VALUES ($1, $2) RETURNING *
```

**Validation:**
- `shopName` is required, must be a non-empty string
- Trims whitespace from the name

**Response:**
```json
{
  "shop_id": 2,
  "shop_name": "New Shop"
}
```

**Implementation:** [`src/server/api/shops/index.post.ts`](src/server/api/shops/index.post.ts)

---

#### PUT `/api/shops/:id`

Update an existing shop's name.

**Request Body:**
```json
{
  "shopName": "Updated Shop Name"
}
```

**Database Queries:**
```sql
-- Check if shop exists
SELECT shop_name FROM bre_shops WHERE shop_id = $1

-- Update the shop
UPDATE bre_shops SET shop_name = $1 WHERE shop_id = $2 RETURNING shop_id, shop_name
```

**Validation:**
- `id` (router param) is required, must be a valid integer
- `shopName` is required, must be a non-empty string
- Returns 404 if shop not found

**Response:**
```json
{
  "shop_id": 1,
  "shop_name": "Updated Shop Name"
}
```

**Implementation:** [`src/server/api/shops/[id].put.ts`](src/server/api/shops/[id].put.ts)

---

#### DELETE `/api/shops/:id`

Delete a shop and unlink all associated accounts.

**Database Queries:**
```sql
-- First, unlink all accounts from this shop
DELETE FROM bre_shop_account_matrix WHERE shop_id = $1

-- Then delete the shop
DELETE FROM bre_shops WHERE shop_id = $2
```

**Validation:**
- `id` (router param) is required, must be a valid integer

**Response:**
```json
{
  "success": true,
  "shopId": 1
}
```

**Implementation:** [`src/server/api/shops/[id].delete.ts`](src/server/api/shops/[id].delete.ts)

---

### Shop Accounts API

#### GET `/api/shops/:id/accounts`

List all accounts linked to a specific shop.

**Database Query:**
```sql
SELECT sam.account_id, a.account_name
FROM bre_shop_account_matrix sam
INNER JOIN bre_shop_account a ON sam.account_id = a.account_id
WHERE sam.shop_id = $1
```

**Query Parameters:** None (shop ID from router param)

**Validation:**
- `id` (router param) is required, must be a valid integer
- Returns 404 if shop not found

**Response:**
```json
[
  {
    "account_id": 1,
    "account_name": "Artist Account"
  }
]
```

**Implementation:** [`src/server/api/shops/[id]/accounts.get.ts`](src/server/api/shops/[id]/accounts.get.ts)

---

#### POST `/api/shops/:id/accounts`

Link an account to a shop.

**Request Body:**
```json
{
  "accountId": 1
}
```

**Database Query:**
```sql
INSERT INTO bre_shop_account_matrix (shop_id, account_id) VALUES ($1, $2)
```

**Validation:**
- `id` (router param) and `accountId` (body) are required

**Response:**
```json
{
  "success": true
}
```

**Implementation:** [`src/server/api/shops/[id]/accounts.post.ts`](src/server/api/shops/[id]/accounts.post.ts)

---

#### DELETE `/api/shops/:id/accounts`

Unlink an account from a shop.

**Request Body:**
```json
{
  "accountId": 1
}
```

**Database Query:**
```sql
DELETE FROM bre_shop_account_matrix
WHERE shop_id = $1 AND account_id = $2
```

**Validation:**
- `id` (router param) and `accountId` (body) are required

**Response:**
```json
{
  "success": true
}
```

**Implementation:** [`src/server/api/shops/[id]/accounts.delete.ts`](src/server/api/shops/[id]/accounts.delete.ts)

---

#### GET `/api/shops/:id/accounts-with-files`

List accounts linked to a shop with file counts **filtered by shop**. Only counts files that belong to this specific shop via `bre_shops_index`.

**Database Query:**
```sql
SELECT
  a.account_id,
  a.account_name,
  COUNT(DISTINCT CASE WHEN si.shop_id = $1 THEN ai.file_id END) AS file_count
FROM bre_shop_account a
INNER JOIN bre_shop_account_matrix sam ON a.account_id = sam.account_id
LEFT JOIN bre_account_index ai ON a.account_id = ai.account_id
LEFT JOIN bre_shops_index si ON CAST(ai.file_id AS text) = si.id
WHERE sam.shop_id = $1
GROUP BY a.account_id, a.account_name
```

**Key Logic:** The `CASE` expression ensures only files linked to the current shop are counted, even if the account has files linked to other shops.

**Validation:**
- `id` (router param) is required, must be a valid integer
- Returns 404 if shop not found

**Response:**
```json
[
  {
    "account_id": 1,
    "account_name": "Artist Account",
    "file_count": 42
  }
]
```

**Implementation:** [`src/server/api/shops/[id]/accounts-with-files.get.ts`](src/server/api/shops/[id]/accounts-with-files.get.ts)

---

### Shop Files API

#### GET `/api/shops/:id/files`

List files for a shop, optionally filtered by account.

**Database Query:**
```sql
SELECT
  ai.fileid,
  ai.name,
  ai.preview_url,
  aci.account_id,
  a.account_name
FROM bre_advance_index ai
INNER JOIN bre_shops_index si ON CAST(ai.fileid AS bigint) = si.id
INNER JOIN bre_account_index aci ON CAST(ai.fileid AS bigint) = aci.file_id
INNER JOIN bre_shop_account a ON aci.account_id = a.account_id
WHERE si.shop_id = $1
  AND (aci.account_id = $2)  -- optional, if accountId provided
LIMIT $3 OFFSET $4
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `accountId` | string | No | - | Filter by account ID |
| `limit` | integer | No | 50 | Maximum results |
| `offset` | integer | No | 0 | Pagination offset |

**Validation:**
- `id` (router param) is required, must be a valid integer
- `accountId` if provided must be a valid integer

**Implementation:** [`src/server/api/shops/[id]/files.get.ts`](src/server/api/shops/[id]/files.get.ts)

---

#### GET `/api/shops/:id/files/search`

Search files by filename or display name within a specific shop and account.

**Database Query:**
```sql
SELECT
  ai.fileid,
  ai.name,
  ai.preview_url,
  aci.account_id,
  a.account_name
FROM bre_advance_index ai
INNER JOIN bre_shops_index si ON CAST(ai.fileid AS bigint) = si.id
INNER JOIN bre_account_index aci ON CAST(ai.fileid AS bigint) = aci.file_id
INNER JOIN bre_shop_account a ON aci.account_id = a.account_id
LEFT JOIN bre_display_name_index dni ON CAST(ai.fileid AS bigint) = dni.file_id
LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
WHERE si.shop_id = $1
  AND aci.account_id = $2
  AND (ai.name ILIKE $3 OR dn.display_name ILIKE $3)
LIMIT $4 OFFSET $5
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search term (ILIKE wildcard) |
| `accountId` | string | Yes | - | Account to search within |
| `limit` | integer | No | 50 | Maximum results |
| `offset` | integer | No | 0 | Pagination offset |

**Post-Processing:** Results are deduplicated by `fileId` in JavaScript (since the LEFT JOIN can produce duplicate rows when a file has multiple display names).

**Validation:**
- `id`, `query`, and `accountId` are all required
- `query` must be non-empty after trimming

**Implementation:** [`src/server/api/shops/[id]/files/search.get.ts`](src/server/api/shops/[id]/files/search.get.ts)

---

#### GET `/api/shops/:id/all-files`

Get all files for a shop across all linked accounts.

**Database Queries:**
```sql
-- Step 1: Get all account IDs linked to this shop
SELECT account_id FROM bre_shop_account_matrix WHERE shop_id = $1

-- Step 2: Fetch files for those accounts
SELECT
  ai.fileid,
  ai.name,
  ai.preview_url,
  aci.account_id,
  a.account_name
FROM bre_advance_index ai
INNER JOIN bre_account_index aci ON CAST(ai.fileid AS bigint) = aci.file_id
INNER JOIN bre_shop_account a ON aci.account_id = a.account_id
WHERE aci.account_id = ANY($1::bigint[])
LIMIT $2 OFFSET $3
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `accountId` | string | No | - | Optional: further filter by specific account |
| `limit` | integer | No | 50 | Maximum results |
| `offset` | integer | No | 0 | Pagination offset |

**Implementation:** [`src/server/api/shops/[id]/all-files.get.ts`](src/server/api/shops/[id]/all-files.get.ts)

---

#### GET `/api/shops/:id/linked-files-search`

Advanced linked file search with support for text search, account filtering, and preview URL transformation. Queries the `bre_file_junction` table (source of truth) instead of the older index tables.

**Database Query (Main):**
```sql
SELECT
  ai.fileid AS "fileId",
  ai.name AS "filename",
  ai.preview_url AS "previewUrl",
  MAX(dn.display_name) AS "displayName",
  (ARRAY_AGG(DISTINCT fj.account_id)) AS "accountIds",
  (
    SELECT ARRAY_AGG(DISTINCT sa2.account_name ORDER BY sa2.account_name)
    FROM bre_file_junction fj2
    JOIN bre_shop_account sa2 ON fj2.account_id = sa2.account_id
    WHERE fj2.file_id = ai.fileid AND fj2.shop_id = $1
  ) AS "accountNames"
FROM bre_advance_index ai
INNER JOIN bre_file_junction fj ON ai.fileid::text = fj.file_id
INNER JOIN bre_shop_account sa ON fj.account_id = sa.account_id
LEFT JOIN bre_display_name_index dni ON ai.fileid::text = dni.file_id
LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
WHERE fj.shop_id = $1
GROUP BY ai.fileid, ai.name, ai.preview_url
ORDER BY ai.fileid
LIMIT $2 OFFSET $3
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | No | - | Text search (ILIKE) |
| `accountId` | string | No | - | Filter by account |
| `limit` | integer | No | 15 | Maximum results |
| `offset` | integer | No | 0 | Pagination offset |
| `previewSize` | integer | No | 64 | Thumbnail dimensions for preview URLs |

**Post-Processing:** Preview URLs are transformed using `transformPreviewUrls()` to convert database paths into local proxy URLs.

**Validation:**
- `id` (router param) is required, must be a valid integer
- `accountId` if provided must be a valid integer

**Response:**
```json
[
  {
    "fileId": 1,
    "filename": "image.jpg",
    "previewUrl": "/api/files/preview-proxy/1?x=64&y=64",
    "displayName": "My Image",
    "accountIds": [1, 3],
    "accountNames": ["Account A", "Account C"]
  }
]
```

**Note:** The response now includes `accountIds` and `accountNames` arrays showing all accounts linked to this file within the shop.

**Implementation:** [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts)

---

### Accounts API

#### GET `/api/accounts`

List all accounts with shop counts.

**Database Query:**
```sql
SELECT
  a.account_id,
  a.account_name,
  COUNT(s.shop_id) AS shop_count
FROM bre_shop_account a
LEFT JOIN bre_shop_account_matrix sam ON a.account_id = sam.account_id
LEFT JOIN bre_shops s ON sam.shop_id = s.shop_id
GROUP BY a.account_id, a.account_name
ORDER BY a.account_name ASC
```

**Response:**
```json
[
  {
    "account_id": 1,
    "account_name": "Artist Account",
    "shop_count": 3
  }
]
```

**Implementation:** [`src/server/api/accounts/index.get.ts`](src/server/api/accounts/index.get.ts)

---

#### POST `/api/accounts`

Create a new account with an explicit ID.

**Request Body:**
```json
{
  "accountName": "New Account"
}
```

**Database Query:**
```sql
-- Get next available ID
SELECT MAX(account_id) AS max FROM bre_shop_account

-- Insert with explicit ID
INSERT INTO bre_shop_account (account_id, account_name) VALUES ($1, $2) RETURNING *
```

**Validation:**
- `accountName` is required, must be a non-empty string
- Trims whitespace from the name

**Response:**
```json
{
  "account_id": 5,
  "account_name": "New Account"
}
```

**Implementation:** [`src/server/api/accounts/index.post.ts`](src/server/api/accounts/index.post.ts)

---

#### DELETE `/api/accounts/:id`

Delete an account and remove all associations.

**Database Queries:**
```sql
-- First, remove all shop associations
DELETE FROM bre_shop_account_matrix WHERE account_id = $1

-- Remove all file associations
DELETE FROM bre_account_index WHERE account_id = $2

-- Then delete the account
DELETE FROM bre_shop_account WHERE account_id = $3
```

**Validation:**
- `id` (router param) is required, must be a valid integer

**Response:**
```json
{
  "success": true,
  "accountId": 1
}
```

**Implementation:** [`src/server/api/accounts/[id].delete.ts`](src/server/api/accounts/[id].delete.ts)

---

### Files API (Global)

#### GET `/api/files`

List all files with shop and account information.

**Database Query:**
```sql
SELECT
  ai.fileid,
  ai.name,
  ai.preview_url,
  si.shop_id,
  s.shop_name,
  sam.account_id,
  a.account_name
FROM bre_advance_index ai
LEFT JOIN bre_shops_index si ON ai.fileid = si.id
LEFT JOIN bre_shops s ON si.shop_id = s.shop_id
LEFT JOIN bre_shop_account_matrix sam ON s.shop_id = sam.shop_id
LEFT JOIN bre_shop_account a ON sam.account_id = a.account_id
ORDER BY ai.name ASC
```

**Implementation:** [`src/server/api/files/index.get.ts`](src/server/api/files/index.get.ts)

---

#### POST `/api/files`

Create a new file entry and optionally link it to a shop.

**Request Body:**
```json
{
  "name": "filename.jpg",
  "previewUrl": "/core/preview?fileId=123&{prevsize}",
  "shopId": 1
}
```

**Database Queries:**
```sql
-- Insert file
INSERT INTO bre_advance_index (name, preview_url) VALUES ($1, $2) RETURNING *

-- Optionally link to shop
INSERT INTO bre_shops_index (id, shop_id) VALUES ($1, $2)
```

**Validation:**
- `name` is required, must be a non-empty string

**Implementation:** [`src/server/api/files/index.post.ts`](src/server/api/files/index.post.ts)

---

#### GET `/api/files/:fileId/tags`

Get tags (display names) for a specific file.

**Database Query:**
```sql
SELECT dn.display_name
FROM bre_display_name_index dni
INNER JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
WHERE dni.file_id = $1
```

**Response:**
```json
["Tag1", "Tag2", "Tag3"]
```

**Implementation:** [`src/server/api/files/[fileId]/tags.get.ts`](src/server/api/files/[fileId]/tags.get.ts)

---

#### GET `/api/files/search-by-name`

Search files by filename or display name across all accounts.

**Database Query:**
```sql
SELECT DISTINCT ON (ai.fileid)
  ai.fileid AS "fileId",
  ai.name AS "filename",
  ai.preview_url AS "previewUrl",
  dn.display_name AS "displayName"
FROM bre_advance_index ai
LEFT JOIN bre_display_name_index dni ON ai.fileid::text = dni.file_id
LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
WHERE ai.name ILIKE $1 OR dn.display_name ILIKE $1
ORDER BY ai.fileid
LIMIT $2
```

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search term (ILIKE) |
| `limit` | integer | No | 10 | Maximum results |
| `previewSize` | integer | No | 540 | Thumbnail dimensions for preview URLs |

**Implementation:** [`src/server/api/files/search-by-name.get.ts`](src/server/api/files/search-by-name.get.ts)

---

#### POST `/api/files/link-to-shop-account`

Link a file to both a shop and an account by inserting a triadic relationship into the `bre_file_junction` table.

**Request Body:**
```json
{
  "fileId": 123,
  "shopId": 1,
  "accountId": 5
}
```

**Database Query:**
```sql
-- Insert triadic relationship (shop + file + account)
-- ON CONFLICT DO NOTHING prevents duplicate entries
INSERT INTO bre_file_junction (shop_id, file_id, account_id)
VALUES ($1, $2, $3)
ON CONFLICT DO NOTHING
```

**Validation:**
- `fileId`, `shopId`, and `accountId` are all required

**Response:**
```json
{
  "success": true,
  "fileId": 123,
  "shopId": 1,
  "accountId": 5
}
```

**Implementation:** [`src/server/api/files/link-to-shop-account.post.ts`](src/server/api/files/link-to-shop-account.post.ts)

---

#### POST `/api/files/unlink`

Unlink a file from a shop and optionally from a specific account. Deletes the relationship from the `bre_file_junction` table.

**Request Body:**
```json
{
  "fileId": 123,
  "shopId": 1,
  "accountId": 5  // optional
}
```

**Database Queries:**

*When `accountId` is provided (unlink from specific account):*
```sql
DELETE FROM bre_file_junction
WHERE shop_id = $1 AND file_id = $2 AND account_id = $3
```

*When `accountId` is omitted (unlink file from shop entirely across all accounts):*
```sql
DELETE FROM bre_file_junction
WHERE shop_id = $1 AND file_id = $2
```

**Validation:**
- `fileId` and `shopId` are required
- `accountId` is optional - controls granularity of unlink

**Response:**
```json
{
  "success": true,
  "fileId": 123,
  "shopId": 1,
  "accountId": 5
}
```

**Implementation:** [`src/server/api/files/unlink.post.ts`](src/server/api/files/unlink.post.ts)

---

#### POST `/api/files/reverse-search`

Reverse image search using perceptual hashing. Accepts an uploaded image, calculates hashes via Python subprocess, and returns the closest matches from the database.

**Request:** `multipart/form-data`
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | File | Yes | - | Uploaded image file |
| `hashMethod` | string | No | `whash` | One of: `whash`, `ahash`, `phash`, `average` |

**Database Query:**
```sql
SELECT
  h.id AS "fileId",
  ai.name AS "filename",
  ai.preview_url AS "previewUrl",
  dn.display_name AS "displayName",
  h.w_hash,
  h.a_hash,
  h.p_hash
FROM bre_hashes h
INNER JOIN bre_advance_index ai ON h.id = ai.fileid::text
LEFT JOIN bre_display_name_index dni ON h.id = dni.file_id
LEFT JOIN bre_display_names dn ON dni.display_name_id = dn.display_name_id
```

**Hash Calculation Flow:**
1. Image is read as multipart form data
2. Image bytes are base64-encoded and sent to Python subprocess (`src/py-code/hash_helper.py`)
3. Python script calculates `whash`, `ahash`, and `phash` using the `imagehash` library
4. Hashes are returned as base64-encoded JSON via stdout
5. Node.js computes Hamming distances client-side for all database entries
6. Results are ranked by minimum distance across all hash methods
7. Top 10 results are returned, re-sorted by the selected hash method

**Hamming Distance Calculation:**
```typescript
function hexHammingDistance(hex1: string, hex2: string): number {
  // Split into two 32-bit parts to avoid floating point issues
  const high1 = parseInt(hex1.substring(0, 8), 16)
  const low1 = parseInt(hex1.substring(8, 16), 16)
  const high2 = parseInt(hex2.substring(0, 8), 16)
  const low2 = parseInt(hex2.substring(8, 16), 16)
  
  const xorHigh = high1 ^ high2
  const xorLow = low1 ^ low2
  
  // Popcount using lookup table
  const table = [0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4]
  function popcount(n: number): number {
    let count = 0
    while (n) {
      count += table[n & 0xF]
      n >>>= 4
    }
    return count
  }
  
  return popcount(xorHigh) + popcount(xorLow)
}
```

**Response:**
```json
[
  {
    "fileId": 123,
    "filename": "image.jpg",
    "displayName": "My Image",
    "previewUrl": "/api/files/preview-proxy/123?x=540&y=540",
    "whashDistance": 4,
    "ahashDistance": 6,
    "phashDistance": 8,
    "combinedDistance": 4,
    "rank": 1,
    "isBestMatch": true
  }
]
```

**Implementation:** [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts)

---

#### GET `/api/files/preview-proxy/:fileId`

Proxy endpoint for fetching authenticated preview images from Nextcloud.

The Nextcloud `/core/preview` endpoint requires Basic Authentication. This proxy fetches the image with credentials and returns it directly to the browser.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `fileId` | string | The file ID from the database |

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `size` | integer | No | 64 | Image dimension (sets both x and y) |
| `x` | integer | No | size | Custom width |
| `y` | integer | No | size | Custom height |

**Nextcloud Request:**
```
GET http://{NC_HOST}:8080/core/preview?fileId={fileId}&x={x}&y={y}
Headers: Authorization: Basic {base64(NC_ACC:NC_PASS)}
Response-Type: blob
```

**Response:**
```
HTTP 200
Content-Type: image/jpeg
Cache-Control: public, max-age=3600

<binary JPEG data>
```

**Implementation:** [`src/server/api/files/preview-proxy/[fileId].get.ts`](src/server/api/files/preview-proxy/[fileId].get.ts)

---

## Composables

### useLinkedFiles ([`src/composables/useLinkedFiles.ts`](src/composables/useLinkedFiles.ts))

Manages the state and logic for browsing linked files in a hierarchical manner (Shop -> Account -> Files).

#### State

| Property | Type | Description |
|----------|------|-------------|
| `selectedShop` | `Ref<Shop \| null>` | Currently selected shop |
| `selectedAccount` | `Ref<{accountId, accountName} \| null>` | Currently selected account |
| `searchQuery` | `Ref<string>` | Current search query |
| `linkedFiles` | `Ref<LinkedFileResult[]>` | List of linked files |
| `shopAccounts` | `Ref<ShopAccountWithFileCount[]>` | Accounts for selected shop with file counts |
| `loading` | `Ref<boolean>` | Loading state |
| `searchLoading` | `Ref<boolean>` | Search loading state |
| `offset` | `Ref<number>` | Pagination offset |
| `hasMore` | `Ref<boolean>` | Whether more files are available |
| `visibleRows` | `Ref<number>` | Number of visible rows (calculated from viewport) |

#### Methods

| Method | Parameters | Description |
|--------|------------|-------------|
| `selectShop` | `shop: Shop` | Select a shop and load its accounts and files |
| `selectAccount` | `account: {accountId, accountName}` | Drill down to a specific account's files |
| `goBackToShopList` | None | Clear all selections, return to shop list |
| `goBackToShopView` | None | Clear account selection, return to shop view |
| `performSearch` | `query: string` | Debounced text search (300ms delay) |
| `loadMore` | None | Load more files (pagination) |
| `clearSelection` | None | Alias for `goBackToShopList` |
| `calculateVisibleRows` | `availableHeight: number` | Calculate visible rows from viewport height |
| `setupResizeObserver` | `element: HTMLElement \| null` | Set up resize observer for dynamic row calculation |

#### Internal API Calls

| Function | API Endpoint | Description |
|----------|--------------|-------------|
| `fetchAccounts` | `GET /api/shops/{shopId}/accounts-with-files` | Load accounts with file counts |
| `fetchFiles` | `GET /api/shops/{shopId}/linked-files-search` | Load files with optional account/query filter |

#### Features

- **Preview URL Transformation**: Backend transforms database `preview_url` values into proxy URLs
- **Multi-account support**: Response includes `accountIds` and `accountNames` arrays showing all accounts linked to each file
- **Viewport-based lazy loading**: Calculates visible rows based on container height (row height = 80px: 64px thumbnail + padding + text)
- **Debounced search**: 300ms debounce on search input to reduce API calls
- **AbortController**: Cancels pending requests when new searches are triggered
- **Auto-cleanup**: Uses `onUnmounted` to clean up ResizeObserver, timers, and abort controllers
- **Pagination**: Supports infinite scroll with `loadMore`

---

### useLinkFiles ([`src/composables/useLinkFiles.ts`](src/composables/useLinkFiles.ts))

Manages file linking functionality including filename search, reverse image search, and linking files to shops/accounts.

#### State

| Property | Type | Description |
|----------|------|-------------|
| `searchMode` | `Ref<SearchMode>` | Current search mode: `'filename'` or `'reverse'` |
| `searchQuery` | `Ref<string>` | Current search query |
| `searchResults` | `Ref<LinkFileResult[]>` | Search results |
| `showLinkMenu` | `Ref<boolean>` | Link menu visibility |
| `selectedFile` | `Ref<LinkFileResult \| null>` | Currently selected file for linking |
| `selectedShopId` | `Ref<number \| null>` | Selected shop ID in link menu |
| `selectedAccountId` | `Ref<number \| null>` | Selected account ID in link menu |
| `shops` | `Ref<Shop[]>` | List of shops |
| `accounts` | `Ref<Account[]>` | Accounts for selected shop |
| `uploadedImage` | `Ref<File \| null>` | Uploaded image for reverse search |
| `selectedHashMethod` | `Ref<HashMethod>` | Hash method: `'whash'` \| `'ahash'` \| `'phash'` \| `'average'` |
| `exceedsLimit` | `Ref<boolean>` | Whether results exceeded the limit |
| `searchLoading` | `Ref<boolean>` | Search loading state |
| `uploadLoading` | `Ref<boolean>` | Upload/loading state |
| `uploadError` | `Ref<string \| null>` | Upload error message |
| `searchError` | `Ref<string \| null>` | Search error message |

#### Methods

| Method | Parameters | Description |
|--------|------------|-------------|
| `searchByFilename` | `query: string` | Search files by filename or display name |
| `reverseSearch` | `imageFile: File` | Perform reverse image search |
| `linkFileToShopAccount` | `fileId, shopId, accountId` | Link a file to a shop and account |
| `openLinkMenu` | `file: LinkFileResult` | Open link menu for a file |
| `closeLinkMenu` | None | Close link menu |
| `onShopChange` | `shopId: number` | Handle shop selection (loads accounts) |
| `onAccountChange` | `accountId: number` | Handle account selection |
| `handleImageUpload` | `event: Event` | Handle file input change |
| `handleDrop` | `event: DragEvent` | Handle drag and drop |
| `switchMode` | `mode: SearchMode` | Switch between filename and reverse search |
| `clearResults` | None | Clear all search results |

#### Internal API Calls

| Function | API Endpoint | Description |
|----------|--------------|-------------|
| `fetchShops` | `GET /api/shops` | Load all shops |
| `fetchAccounts` | `GET /api/shops/{shopId}/accounts` | Load accounts for a shop |
| `searchByFilename` | `GET /api/files/search-by-name?query=&limit=10&previewSize=540` | Search by filename |
| `reverseSearch` | `POST /api/files/reverse-search` | Reverse image search |
| `linkFileToShopAccount` | `POST /api/files/link-to-shop-account` | Link file to shop and account |

---

### useShops ([`src/composables/useShops.ts`](src/composables/useShops.ts))

Manages shop list state and CRUD operations.

#### State

| Property | Type | Description |
|----------|------|-------------|
| `shops` | `Ref<Shop[]>` | List of all shops |
| `loading` | `Ref<boolean>` | Loading state |
| `error` | `Ref<string \| null>` | Error message |

#### Methods

| Method | Parameters | Description |
|--------|------------|-------------|
| `fetchShops` | None | Fetch all shops from API |
| `createShop` | `name: string` | Create a new shop |

#### Lifecycle

Automatically fetches shops on component mount via `onMounted`.

#### Internal API Calls

| Function | API Endpoint | Description |
|----------|--------------|-------------|
| `fetchShops` | `GET /api/shops` | Load all shops |
| `createShop` | `POST /api/shops` | Create a new shop |

---

### useTheme ([`src/composables/useTheme.ts`](src/composables/useTheme.ts))

Manages application theme (light/dark mode).

#### State

| Property | Type | Description |
|----------|------|-------------|
| `theme` | `Ref<Theme>` | Current theme (`'light'` or `'dark'`) |

#### Methods

| Method | Parameters | Description |
|--------|------------|-------------|
| `applyTheme` | `t: Theme` | Apply theme to document and localStorage |
| `toggleTheme` | None | Toggle between light and dark |

#### Features

- **Persistence**: Saves theme preference to `localStorage` under key `"theme"`
- **System Detection**: Listens for `prefers-color-scheme: dark` media query changes
- **SSR-Safe**: Uses `useState` for SSR-safe state sharing
- **FOUC Prevention**: Theme is applied via inline script in `<head>` before Vue renders

---

## Pages

### Index Page ([`src/pages/index.vue`](src/pages/index.vue))

Simple redirect page that navigates to `/shops`.

**Behavior:**
- Calls `navigateTo('/shops')` in `<script setup>`
- Shows a loading spinner while redirecting

---

### Shops Page ([`src/pages/shops.vue`](src/pages/shops.vue))

Main shop and account management interface.

**Features:**
- Tabbed interface for Shop Management and Accounts views
- Expandable shop list with account/file counts
- Add/Edit/Delete shops via dialog
- Add/Delete accounts
- Link existing accounts to shops via multi-select dialog
- Edit shop names via inline dialog

**State:**
| Variable | Type | Description |
|----------|------|-------------|
| `expandedShops` | `Set<number>` | Set of expanded shop IDs |
| `editingShop` | `{id, name} \| null` | Currently edited shop data |
| `linkingShopId` | `number \| null` | Shop being linked to accounts |
| `selectedAccountIds` | `Set<number>` | Selected accounts for linking |

**API Calls:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/shops` | GET | Load shops |
| `/api/shops` | POST | Create shop |
| `/api/shops/:id` | PUT | Update shop |
| `/api/shops/:id` | DELETE | Delete shop |
| `/api/shops/:id/accounts` | GET | Load shop accounts |
| `/api/shops/:id/accounts` | POST | Link account |
| `/api/shops/:id/accounts` | DELETE | Unlink account |
| `/api/accounts` | GET | Load all accounts |
| `/api/accounts` | POST | Create account |
| `/api/accounts/:id` | DELETE | Delete account |

---

### Files Page ([`src/pages/files.vue`](src/pages/files.vue))

Hierarchical linked files browser.

**Features:**
- Three-state navigation: Shop List -> Shop View -> Account View
- Text search with debouncing (300ms)
- Lazy-loaded image thumbnails (intersection-based)
- Infinite scroll pagination via "Load More" button
- ResizeObserver-based responsive layout

**Navigation States:**
1. **No Selection**: Shows list of all shops
2. **Shop Selected**: Shows accounts and files for the shop
3. **Account Selected**: Shows files for the specific account

**API Calls:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/shops` | GET | Load all shops |
| `/api/shops/:id/linked-files-search` | GET | Load files with pagination |

---

### Link Files Page ([`src/pages/link-files.vue`](src/pages/link-files.vue))

Search for files and link them to shops/accounts.

**Features:**
- Two search modes: Filename search and Reverse image search
- Filename search: Search by filename or display name
- Reverse search: Upload image, calculate perceptual hashes, find similar files
- Link menu: Select shop and account to link a file
- Drag and drop support for image upload
- Hash method selector: whash, ahash, phash, or average

**API Calls:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/shops` | GET | Load shops |
| `/api/shops/:id/accounts` | GET | Load accounts |
| `/api/files/search-by-name` | GET | Search by filename |
| `/api/files/reverse-search` | POST | Reverse image search |
| `/api/files/link-to-shop-account` | POST | Link file |

---

### Browse Page ([`src/pages/browse.vue`](src/pages/browse.vue))

File browsing page with tabbed interface. **Status: Skeleton page** - tab structure is in place but no functionality implemented.

**Tabs:**
- Browse All
- By Shop
- By Account

---

### Performance Page ([`src/pages/performance.vue`](src/pages/performance.vue))

**Status: Skeleton page** - nearly empty, only template structure defined.

---

### Settings Page ([`src/pages/settings.vue`](src/pages/settings.vue))

Application settings with theme toggle.

**Features:**
- Dark mode toggle with switch UI
- Current theme indicator
- Theme persistence via localStorage

**API Calls:** None (purely client-side)

---

## Layouts

### Default Layout ([`src/layouts/default.vue`](src/layouts/default.vue))

Provides the main application layout with a collapsible sidebar.

**Layout Structure:**
```
+------------------+------------------+
| Sidebar (w-64)   | Main Content     |
|                  |                  |
| - Logo           |                  |
| - Navigation     |   <NuxtPage />   |
| - Theme Toggle   |                  |
| - Version Info   |                  |
|                  |                  |
| [Collapse]       |                  |
+------------------+------------------+
```

**Navigation Links:**
| Route | Label | Icon |
|-------|-------|------|
| `/shops` | Shops & Accounts | 🏪 |
| `/files` | Linked Files | 🔗 |
| `/link-files` | Link Files | 🔍 |
| `/browse` | Browse Files | 📂 |
| `/performance` | Performance | 📊 |
| `/settings` | Settings | ⚙️ |

**Sidebar Features:**
- Collapsible with CSS transition (300ms duration)
- Edge hover detection: 10px wide hover zone on left edge triggers expand button
- Mouse Y-position tracking for smooth trigger positioning
- Active route highlighting via `active-class`
- Expand button follows cursor Y position when collapsed

---

## Types

### Shop Types ([`src/types/shop.ts`](src/types/shop.ts))

```typescript
interface Shop {
  shop_id: number
  shop_name: string
  account_count?: number  // Optional: from GET /api/shops
  file_count?: number     // Optional: from GET /api/shops
}

interface ShopFormData {
  shop_name: string
}

interface ShopWithAccounts extends Shop {
  accounts?: Account[]
}
```

### Account Types ([`src/types/account.ts`](src/types/account.ts))

```typescript
interface Account {
  account_id: number
  account_name: string
}

interface AccountFormData {
  account_name: string
}

interface ShopAccountLink {
  shop_id: number
  account_id: number
}
```

### File Types ([`src/types/file.ts`](src/types/file.ts))

```typescript
interface File {
  file_id: number
  filename: string
  display_name?: string
  account_name?: string
  preview_url?: string
  is_linked?: boolean
}

interface FileSearchResult extends File {
  hash_match?: number
}

interface FileFormData {
  file_id: number
  shop_id: number
  account_ids: number[]
}

interface ImageSearchData {
  image: File | Blob
  hashType: 'whash' | 'ahash' | 'phash'
  threshold: number
}
```

### Linked File Types ([`src/types/linkedFile.ts`](src/types/linkedFile.ts))

```typescript
interface LinkedFileResult {
  fileId: number
  filename: string
  previewUrl: string | null
  displayName: string | null
  accountId: number | bigint
  accountName: string
  accountNames: string[]         // All account names linked to this file in the shop
  accountIds: number[]           // All account IDs linked to this file in the shop
}

interface ShopAccountWithFileCount {
  accountId: number | bigint
  accountName: string
  fileCount: number | bigint
}
```

### Link File Types ([`src/types/linkFiles.ts`](src/types/linkFiles.ts))

```typescript
interface LinkFileResult {
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

interface LinkFileRequest {
  fileId: number
  shopId: number
  accountId: number
}

interface HashResult {
  whash: string
  ahash: string
  phash: string
}

type HashMethod = 'whash' | 'ahash' | 'phash' | 'average'
type SearchMode = 'filename' | 'reverse'
```

---

## Utilities

### Database ([`src/lib/db.ts`](src/lib/db.ts))

Singleton PostgreSQL connection pool with Drizzle ORM.

```typescript
function getDb(): DrizzleInstance
const db: DrizzleInstance
```

Uses environment variables with defaults:
| Variable | Default |
|----------|---------|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `shop_management` |
| `DB_USER` | `postgres` |
| `DB_PASSWORD` | `postgres` |

**Implementation:**
```typescript
let pool: Pool | null = null

export function getDb() {
  if (!pool) {
    pool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    })
  }
  return drizzle(pool, { schema })
}

export const db = getDb()
```

---

### Preview URL Transformation ([`src/server/utils/preview.ts`](src/server/utils/preview.ts))

Handles transformation of Nextcloud preview URLs with authentication.

#### `transformPreviewUrl(rawPreviewUrl, size)`

Extracts `fileId` from raw URL and returns proxy URL.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rawPreviewUrl` | `string \| null` | - | Raw preview URL from database (e.g., `/core/preview?fileId=2158&{prevsize}`) |
| `size` | `number` | 64 | Dimension size in pixels |

**Returns:** `string \| null` - Proxy URL (e.g., `/api/files/preview-proxy/2158?x=64&y=64`)

**URL Transformation Flow:**
```
Database: /core/preview?fileId=2158&{prevsize}
              ↓ (extract fileId=2158)
Proxy URL:  /api/files/preview-proxy/2158?x=64&y=64
              ↓ (browser requests)
Server:     Fetch http://NC_HOST:8080/core/preview?fileId=2158&x=64&y=64
            (with Basic Auth NC_ACC:NC_PASS)
              ↓
Return:     Image binary to browser
```

#### `transformPreviewUrls(items, size)`

Bulk transform array of objects with `previewUrl` property.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `items` | `T[]` | Array of objects with `previewUrl` property |
| `size` | `number` | Dimension size in pixels |

**Returns:** Same array with `previewUrl` properties transformed (mutates in place)

---

### Client-Side Utils ([`src/lib/utils.ts`](src/lib/utils.ts))

| Function | Description |
|----------|-------------|
| `cn(...inputs)` | Merge Tailwind CSS classes using `clsx` and `tailwind-merge` |
| `formatFileSize(bytes)` | Format bytes to human-readable string (KB, MB, GB) |
| `truncateString(str, maxLength)` | Truncate string with ellipsis |
| `generateId()` | Generate random string ID |
| `transformPreviewUrl(previewUrl, size)` | Transform preview URL to absolute Nextcloud URL (client-side version) |

---

### Constants ([`src/lib/constants.ts`](src/lib/constants.ts))

```typescript
HASH_TYPES = {
  WHASH: 'whash',
  AHASH: 'ahash',
  PHASH: 'phash',
}

IMAGE_RESIZE_CONFIG = {
  SMALL: { width: 220, height: 220 },
  MEDIUM: { width: 540, height: 540 },
  LARGE: { width: 1080, height: 1080 },
}

DEFAULT_BATCH_SIZE = 20
MAX_BATCH_SIZE = 100

TABS = {
  SHOPS: 'shops',
  ACCOUNTS: 'accounts',
  PERFORMANCE: 'performance',
  OVERVIEW: 'overview',
  ADD_FILES: 'add-files',
}
```

---

## Styling

### Global Styles ([`src/assets/css/global.css`](src/assets/css/global.css))

Uses Tailwind CSS with CSS custom properties for theming.

**CSS Variables (Light Theme):**
```css
--background: 0 0% 100%
--foreground: 222.2 84% 4.9%
--primary: 212.2 83.2% 53.3%
--radius: 0.5rem
```

**CSS Variables (Dark Theme):**
```css
--background: 222.2 84% 4.9%
--foreground: 210 40% 98%
--primary: 217.2 91.2% 59.8%
```

**Tree View Theme Variables:**
- `--tree-bg` - Canvas background gradient
- `--tree-root-bg` - Root node gradient
- `--tree-trunk-bg` - Account node gradient
- `--tree-file-list-bg` - File list background
- `--tree-connection-color` - Connection line color
- And more for zoom controls and previews

### Tailwind Configuration ([`tailwind.config.ts`](tailwind.config.ts))

- Dark mode: `selector` mode (`.dark` class)
- Custom animations: accordion, collapsible
- Custom border radius
- HSL color system using CSS variables

---

## Environment Variables

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host (also used as Nextcloud host fallback) | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `shop_management` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `NC_HOST` | Nextcloud host for preview images | Falls back to `DB_HOST` |
| `NC_ACC` | Nextcloud username (for preview authentication) | `` |
| `NC_PASS` | Nextcloud password (for preview authentication) | `` |

> **Note:** `NC_HOST` is required for preview images to load. If not set, the system falls back to `DB_HOST`. The Nextcloud preview proxy endpoint uses `NC_ACC` and `NC_PASS` for Basic Authentication when fetching images from Nextcloud.

---

## Python Integration

### Hash Helper ([`src/py-code/hash_helper.py`](src/py-code/hash_helper.py))

Python script for calculating perceptual hashes of images. Called via Node.js `child_process.spawn`.

**Input:** Base64-encoded image data via stdin

**Output:** Base64-encoded JSON via stdout

**JSON Response Format:**
```json
{
  "whash": "ff9f030030c23777",
  "ahash": "ffbf070030e377f7",
  "phash": "a499bad95923b287"
}
```

**Error Response Format:**
```json
{
  "error": "Error message"
}
```

**Hash Calculation Process:**
1. Read base64 data from stdin
2. Decode to bytes
3. Open image with PIL (Pillow)
4. Convert to RGB and resize to 1080x1080 (to match database hash values)
5. Calculate three hash types:
   - **whash** (Wavelet Hash): `imagehash.whash(img)` - sensitive to structural changes
   - **ahash** (Average Hash): `imagehash.average_hash(img)` - sensitive to overall brightness
   - **phash** (Perceptual Hash): `imagehash.phash(img)` - sensitive to frequency domain
6. Encode results as base64 JSON
7. Print to stdout

**Dependencies:**
- `Pillow` (PIL) - Image processing
- `imagehash` - Perceptual hash calculation

**Virtual Environment:** Located at `.venv/` in the project root. Python path: `.venv/bin/python`

### RAG Search Service

The application includes a **RAG (Retrieval-Augmented Generation) Search** service built with FastAPI that provides semantic search capabilities using embedding models and TF-IDF weighted document retrieval.

**Key Components:**
- **Embedding Models**: Sentence Transformers (e.g., `qwen3-0.6b`) for encoding text queries and documents
- **TF-IDF Index**: Vectorizer built from file tags/metadata for context-aware retrieval
- **Search Algorithm**: Query encoding → document embeddings → cosine similarity → top-k selection
- **Model Caching**: LRU caching strategy with automatic eviction to manage memory
- **Persistence**: Pre-computed document embeddings and TF-IDF index saved to disk

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/search` | POST | Perform semantic search |
| `/api/v1/rag/models` | GET | List available models |
| `/api/v1/rag/models/current` | GET | Get currently loaded model |
| `/api/v1/rag/models/switch` | POST | Switch to a different model |
| `/api/v1/rag/models/download` | POST | Download a model from HuggingFace |
| `/api/v1/rag/cache/config` | GET/POST | Get/update cache configuration |
| `/api/v1/rag/cache/evict` | POST | Evict unused models from cache |
| `/api/v1/rag/index/rebuild` | POST | Rebuild TF-IDF index from scratch |
| `/api/v1/rag/health` | GET | Health check |

**Nuxt API Proxy Routes:**
- `POST /api/files/rag-search` - Proxies to Python RAG search service
- `GET /api/settings/rag-models` - Lists available RAG models
- `POST /api/settings/rag-model/index` - Switch RAG model
- `GET /api/settings/rag-model/current` - Get current model
- `POST /api/settings/rag-model/download` - Download model
- `POST /api/settings/rag-cache/evict` - Evict cache
- `GET /api/settings/rag-cache-config` - Get cache config
- `POST /api/settings/rag-cache-config` - Update cache config
- `POST /api/settings/rag-index/rebuild` - Rebuild index

For detailed RAG documentation, see [`DOCUMENTATION_RAG.md`](DOCUMENTATION_RAG.md).

---

## Development

### Prerequisites

- Node.js 20+
- PostgreSQL 16+
- Python 3.x with virtual environment
- npm

### Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Configure environment:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your credentials
   ```

3. Set up database:
   ```bash
   npm run db:push    # Push schema to database
   # or
   npm run db:migrate # Run migrations
   ```

4. Start development server:
   ```bash
   npm run dev
   ```

5. Open [http://localhost:3000](http://localhost:3000)

### Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server on port 3000 |
| `npm run build` | Build for production |
| `npm run generate` | Generate static site |
| `npm run preview` | Preview production build |
| `npm run db:generate` | Generate Drizzle migrations |
| `npm run db:migrate` | Run database migrations |
| `npm run db:push` | Push schema directly to database |
| `npm run db:studio` | Open Drizzle Studio (database GUI) |

### Docker Development

1. Start with Docker Compose:
   ```bash
   docker-compose up
   ```

2. The application and database will start together.

3. Access at [http://localhost:3000](http://localhost:3000)

4. Stop with:
   ```bash
   docker-compose down
   ```

---

## Deployment

### Docker Production Build

The [`Dockerfile`](Dockerfile) uses a multi-stage build:

1. **Build Stage**: Installs dependencies and builds the Nuxt application
2. **Production Stage**: Runs the optimized production build

```bash
docker build --build-arg DB_HOST=your-db-host -t shop-management .
docker run -p 3000:3000 -e DB_PASSWORD=your-password shop-management
```

### Environment Variables for Production

Set these environment variables when running the production container:
- `DB_HOST` - Database host
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_PORT` - Database port
- `NC_ACC` - Nextcloud username
- `NC_PASS` - Nextcloud password

---

## File Index

| File | Purpose |
|------|---------|
| [`src/app.vue`](src/app.vue) | Root component |
| [`src/app.config.ts`](src/app.config.ts) | App configuration |
| [`src/env.d.ts`](src/env.d.ts) | Environment type declarations |
| [`src/layouts/default.vue`](src/layouts/default.vue) | Default layout with sidebar |
| [`src/lib/constants.ts`](src/lib/constants.ts) | Application constants |
| [`src/lib/db.ts`](src/lib/db.ts) | Database connection |
| [`src/lib/schema.ts`](src/lib/schema.ts) | Database schema |
| [`src/lib/utils.ts`](src/lib/utils.ts) | Utility functions |
| [`src/composables/useLinkedFiles.ts`](src/composables/useLinkedFiles.ts) | Linked files composable |
| [`src/composables/useLinkFiles.ts`](src/composables/useLinkFiles.ts) | File linking composable |
| [`src/composables/useShops.ts`](src/composables/useShops.ts) | Shops composable |
| [`src/composables/useTheme.ts`](src/composables/useTheme.ts) | Theme composable |
| [`src/pages/index.vue`](src/pages/index.vue) | Home page (redirect) |
| [`src/pages/shops.vue`](src/pages/shops.vue) | Shops management page |
| [`src/pages/files.vue`](src/pages/files.vue) | Linked files page |
| [`src/pages/link-files.vue`](src/pages/link-files.vue) | Link files page |
| [`src/pages/browse.vue`](src/pages/browse.vue) | Browse files page (skeleton) |
| [`src/pages/performance.vue`](src/pages/performance.vue) | Performance page (skeleton) |
| [`src/pages/settings.vue`](src/pages/settings.vue) | Settings page |
| [`src/plugins/theme.ts`](src/plugins/theme.ts) | Theme plugin |
| [`src/types/index.ts`](src/types/index.ts) | Type exports |
| [`src/types/shop.ts`](src/types/shop.ts) | Shop types |
| [`src/types/account.ts`](src/types/account.ts) | Account types |
| [`src/types/file.ts`](src/types/file.ts) | File types |
| [`src/types/linkedFile.ts`](src/types/linkedFile.ts) | Linked file types |
| [`src/types/linkFiles.ts`](src/types/linkFiles.ts) | Link file types |
| [`src/server/api/shops/index.get.ts`](src/server/api/shops/index.get.ts) | List shops |
| [`src/server/api/shops/index.post.ts`](src/server/api/shops/index.post.ts) | Create shop |
| [`src/server/api/shops/[id].put.ts`](src/server/api/shops/[id].put.ts) | Update shop |
| [`src/server/api/shops/[id].delete.ts`](src/server/api/shops/[id].delete.ts) | Delete shop |
| [`src/server/api/shops/[id]/accounts.get.ts`](src/server/api/shops/[id]/accounts.get.ts) | Get shop accounts |
| [`src/server/api/shops/[id]/accounts.post.ts`](src/server/api/shops/[id]/accounts.post.ts) | Link account |
| [`src/server/api/shops/[id]/accounts.delete.ts`](src/server/api/shops/[id]/accounts.delete.ts) | Unlink account |
| [`src/server/api/shops/[id]/accounts-with-files.get.ts`](src/server/api/shops/[id]/accounts-with-files.get.ts) | Accounts with file counts |
| [`src/server/api/shops/[id]/files.get.ts`](src/server/api/shops/[id]/files.get.ts) | Get shop files |
| [`src/server/api/shops/[id]/files/search.get.ts`](src/server/api/shops/[id]/files/search.get.ts) | Search shop files |
| [`src/server/api/shops/[id]/all-files.get.ts`](src/server/api/shops/[id]/all-files.get.ts) | Get all shop files |
| [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts) | Advanced linked file search |
| [`src/server/api/accounts/index.get.ts`](src/server/api/accounts/index.get.ts) | List accounts |
| [`src/server/api/accounts/index.post.ts`](src/server/api/accounts/index.post.ts) | Create account |
| [`src/server/api/accounts/[id].delete.ts`](src/server/api/accounts/[id].delete.ts) | Delete account |
| [`src/server/api/files/index.get.ts`](src/server/api/files/index.get.ts) | List all files |
| [`src/server/api/files/index.post.ts`](src/server/api/files/index.post.ts) | Create file |
| [`src/server/api/files/search-by-name.get.ts`](src/server/api/files/search-by-name.get.ts) | Search by name |
| [`src/server/api/files/link-to-shop-account.post.ts`](src/server/api/files/link-to-shop-account.post.ts) | Link file to shop/account |
| [`src/server/api/files/unlink.post.ts`](src/server/api/files/unlink.post.ts) | Unlink file from shop/account |
| [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts) | Reverse image search |
| [`src/server/api/files/[fileId]/tags.get.ts`](src/server/api/files/[fileId]/tags.get.ts) | Get file tags |
| [`src/server/api/files/preview-proxy/[fileId].get.ts`](src/server/api/files/preview-proxy/[fileId].get.ts) | Preview proxy |
| [`src/server/utils/preview.ts`](src/server/utils/preview.ts) | Preview URL transformation |
| [`src/py-code/hash_helper.py`](src/py-code/hash_helper.py) | Python hash calculation |
| [`src/py-code/rag_search/main.py`](src/py-code/rag_search/main.py) | RAG Search FastAPI app |
| [`src/py-code/rag_search/search.py`](src/py-code/rag_search/search.py) | RAG search logic |
| [`src/py-code/rag_search/database.py`](src/py-code/rag_search/database.py) | RAG database queries |
| [`src/py-code/rag_search/model_loader.py`](src/py-code/rag_search/model_loader.py) | RAG model management |
| [`src/py-code/rag_search/config.py`](src/py-code/rag_search/config.py) | RAG configuration |
| [`src/py-code/rag_search/tfidf_index.py`](src/py-code/rag_search/tfidf_index.py) | TF-IDF index management |
| [`src/composables/useRagSearch.ts`](src/composables/useRagSearch.ts) | RAG search composable |
| [`src/composables/useRAGSettings.ts`](src/composables/useRAGSettings.ts) | RAG settings composable |
| [`src/server/api/files/rag-search.post.ts`](src/server/api/files/rag-search.post.ts) | RAG search API proxy |
| [`src/server/api/settings/rag-models.get.ts`](src/server/api/settings/rag-models.get.ts) | List RAG models |
| [`src/server/api/settings/rag-model/index.post.ts`](src/server/api/settings/rag-model/index.post.ts) | Switch RAG model |
| [`src/server/api/settings/rag-model/current.get.ts`](src/server/api/settings/rag-model/current.get.ts) | Get current model |
| [`src/server/api/settings/rag-model/download.post.ts`](src/server/api/settings/rag-model/download.post.ts) | Download model |
| [`src/server/api/settings/rag-cache/evict.post.ts`](src/server/api/settings/rag-cache/evict.post.ts) | Evict cache |
| [`src/server/api/settings/rag-cache-config/index.get.ts`](src/server/api/settings/rag-cache-config/index.get.ts) | Get cache config |
| [`src/server/api/settings/rag-cache-config/index.post.ts`](src/server/api/settings/rag-cache-config/index.post.ts) | Update cache config |
| [`src/server/api/settings/rag-index/rebuild.post.ts`](src/server/api/settings/rag-index/rebuild.post.ts) | Rebuild index |
| [`DOCUMENTATION_RAG.md`](DOCUMENTATION_RAG.md) | RAG Search documentation |
| [`src/assets/css/global.css`](src/assets/css/global.css) | Global styles |
