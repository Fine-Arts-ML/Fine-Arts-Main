# Shop Management Application - Technical Documentation

> **Last Updated:** 2026-05-08  
> **Version:** 1.0 (TypeScript Conversion)  
> **Framework:** Nuxt 3 (Vue 3 + TypeScript)

---

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
10. [Components](#components)
11. [Types](#types)
12. [Python Services](#python-services)
13. [Development](#development)
14. [Deployment](#deployment)
15. [Dead Code & Deprecations](#dead-code--deprecations)

---

## Overview

The Shop Management Application is a full-stack web application for managing art shops, accounts, and their linked files. It provides CRUD operations for shops and accounts, file management with multiple search capabilities, and integrates with Nextcloud for file previews and Python-based services for perceptual hashing and semantic search.

### Key Features

| Feature | Description |
|---------|-------------|
| **Shop Management** | Create, read, update, and delete shops via [`shops.vue`](src/pages/shops.vue) |
| **Account Management** | Create, read, and delete accounts linked to shops |
| **Shop-Account Linking** | Many-to-many relationship via `bre_shop_account_matrix` |
| **File Search** | Four search modes: semantic (RAG), name-based, browse-all, reverse image search |
| **Linked Files Browser** | Hierarchical browsing of files by shop and account with pagination |
| **File Linking/Unlinking** | Link files to shops/accounts via `bre_file_junction` triadic relationship |
| **Published Status** | Toggle file published/unpublished status |
| **Display Names** | Link, unlink, and edit display names for shops, accounts, and files |
| **Reverse Image Search** | Perceptual hash-based image similarity search (whash, ahash, phash) |
| **RAG Semantic Search** | Natural language search using embedding models and TF-IDF |
| **Theme Support** | Light/dark mode with system preference detection |
| **Nextcloud Integration** | Fetch preview images from Nextcloud servers via authenticated proxy |

---

## Architecture

The application follows the Nuxt 3 full-stack architecture:

```
User Action -> Vue Component -> Composable -> Server API Route -> PostgreSQL
                                      -> Python Service (RAG/Hash)
                                       <-             <-
```

### Data Flow

1. User interacts with a Vue page component
2. Page calls a composable function
3. Composable makes `$fetch` calls to server API routes
4. API routes query PostgreSQL via Drizzle ORM or raw `pg` pool
5. For RAG search, API routes proxy to Python FastAPI service
6. Results flow back through the composable to the component

### Architecture Notes

- **Dual Database Access:** Some API routes use Drizzle ORM (`~/lib/db`) for type-safe queries, while others use raw `pg` pool for complex SQL (e.g., `linked-files-search`, `reverse-search`). This is because the underlying database schema uses non-standard table/column names (`bre_` prefix) that are not fully modeled in Drizzle.
- **SSR-Compatible Theme:** Theme is applied via an inline synchronous script in `<head>` (before Vue renders) to prevent FOUC (Flash of Unstyled Content). Vue syncs with the DOM state on mount.
- **Consolidated File Search:** All file search functionality (semantic, name, browse-all, reverse image) is consolidated into a single page [`files.vue`](src/pages/files.vue) with tab-based navigation.

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
| Icon Library | Lucide Vue Next | 0.400+ |
| Date Handling | date-fns | 3.6+ |
| Image Processing | JIMP | 0.22+ |
| Python Framework | FastAPI | (RAG service) |
| Image Hashing | imagehash (Python) | (reverse search) |
| Embeddings | Sentence Transformers | (RAG service) |

---

## Project Structure

```
shop_management_app/
├── src/
│   ├── app.config.ts                    # App-wide configuration
│   ├── app.vue                          # Root application component
│   ├── env.d.ts                         # Environment type declarations
│   ├── assets/
│   │   └── css/
│   │       ├── global.css               # Global styles + CSS variables for theming
│   │       └── tree-view.css            # Tree view visualization styles
│   ├── components/
│   │   └── ImagePreviewModal.vue        # Image preview modal component
│   ├── composables/                     # Vue composables (reactive logic)
│   │   ├── useImagePreview.ts           # Image preview modal logic
│   │   ├── useLinkedFiles.ts            # Linked files browsing (Shop -> Account -> Files)
│   │   ├── useLinkFiles.ts              # File linking (search, reverse search, link)
│   │   ├── useRagSearch.ts              # RAG semantic search logic
│   │   ├── useRAGSettings.ts            # RAG settings management
│   │   ├── useShops.ts                  # Shop management logic
│   │   └── useTheme.ts                  # Theme toggle logic
│   ├── layouts/
│   │   └── default.vue                  # Default layout with collapsible sidebar
│   ├── lib/
│   │   ├── constants.ts                 # App constants (hash types, image sizes, tabs)
│   │   ├── db.ts                        # Database connections (Drizzle + pg Pool)
│   │   ├── schema.ts                    # Drizzle ORM schema definitions
│   │   └── utils.ts                     # Helper utilities
│   ├── pages/                           # File-based routing
│   │   ├── index.vue                    # Home page (redirects to /shops)
│   │   ├── shops.vue                    # Shop & Account management
│   │   ├── files.vue                    # File search (RAG, name, browse, reverse)
│   │   ├── linked-files.vue             # Linked files browser
│   │   ├── performance.vue              # Placeholder page
│   │   └── settings.vue                 # RAG & theme settings
│   ├── plugins/
│   │   └── theme.ts                     # Theme plugin for initial sync
│   ├── py-code/
│   │   ├── hash_calc/                   # Perceptual hash calculation service
│   │   │   ├── main.py                  # FastAPI hash calculation app
│   │   │   ├── config.py                # Hash calculation configuration
│   │   │   └── requirements.txt         # Python dependencies
│   │   └── rag_search/                  # RAG Search FastAPI service
│   │       ├── main.py                  # FastAPI application
│   │       ├── search.py                # Core search logic
│   │       ├── database.py              # Database connection handler
│   │       ├── model_loader.py          # Embedding model loading/caching
│   │       ├── config.py                # RAG configuration
│   │       ├── tfidf_index.py           # TF-IDF vectorization
│   │       └── requirements.txt         # Python dependencies
│   ├── server/
│   │   ├── api/
│   │   │   ├── accounts/
│   │   │   │   ├── index.get.ts         # List all accounts
│   │   │   │   ├── index.post.ts        # Create account
│   │   │   │   └── [id].delete.ts       # Delete account
│   │   │   ├── files/
│   │   │   │   ├── search-by-name.get.ts    # Search by filename/display name
│   │   │   │   ├── link-to-shop-account.post.ts # Link file to shop+account
│   │   │   │   ├── unlink.post.ts             # Unlink file from shop/account
│   │   │   │   ├── published.put.ts             # Update published status
│   │   │   │   ├── reverse-search.post.ts     # Reverse image search
│   │   │   │   ├── rag-search.post.ts       # RAG semantic search proxy
│   │   │   │   ├── browse-all.get.ts      # Browse all files
│   │   │   │   ├── [fileId]/
│   │   │   │   │   └── tags.get.ts        # Get tags for a file
│   │   │   │   └── preview-proxy/
│   │   │   │       └── [fileId].get.ts    # Proxy for Nextcloud previews
│   │   │   ├── settings/
│   │   │   │   ├── rag-models.get.ts          # List RAG models
│   │   │   │   ├── rag-cache/
│   │   │   │   │   └── evict.post.ts          # Evict cache
│   │   │   │   ├── rag-cache-config/
│   │   │   │   │   ├── index.get.ts           # Get cache config
│   │   │   │   │   └── index.post.ts          # Update cache config
│   │   │   │   ├── rag-index/
│   │   │   │   │   └── rebuild.post.ts        # Rebuild TF-IDF index
│   │   │   │   └── rag-model/
│   │   │   │       ├── current.get.ts         # Get current model
│   │   │   │       ├── download.post.ts       # Download model
│   │   │   │       └── index.post.ts          # Switch model
│   │   │   └── shops/
│   │   │       ├── index.get.ts               # List all shops
│   │   │       ├── index.post.ts              # Create shop
│   │   │       ├── [id].delete.ts             # Delete shop
│   │   │       ├── [id].put.ts                # Update shop
│   │   │       └── [id]/
│   │   │           ├── accounts.get.ts            # Get shop accounts
│   │   │           ├── accounts.post.ts           # Link account to shop
│   │   │           ├── accounts.delete.ts         # Unlink account from shop
│   │   │           ├── accounts-with-files.get.ts # Accounts with file counts
│   │   │           ├── files.get.ts               # Get shop files
│   │   │           ├── files.search.get.ts        # Search shop files
│   │   │           ├── all-files.get.ts           # Get all shop files
│   │   │           ├── linked-files-search.get.ts # Advanced linked file search
│   │   │           └── [id]/
│   │   │               └── ...
│   │   └── utils/
│   │       └── preview.ts               # Preview URL transformation utilities
│   └── types/
│       ├── index.ts                     # Type exports
│       ├── shop.ts                      # Shop-related types
│       ├── account.ts                   # Account-related types
│       ├── linkedFile.ts                # Linked file types
│       └── linkFiles.ts                 # File linking types
├── .env.example                         # Environment variables template
├── docker-compose.yml                   # Docker Compose for development
├── Dockerfile                           # Production Docker image
├── Dockerfile.dev                       # Development Docker image
├── drizzle.config.ts                    # Drizzle ORM configuration
├── nuxt.config.ts                       # Nuxt configuration
├── package.json                         # Dependencies and scripts
├── postcss.config.mjs                   # PostCSS configuration
├── DOCUMENTATION.md                     # This file
├── DOCUMENTATION_RAG.md                 # RAG Search documentation
└── DEAD_CODE_ANALYSIS.md                # Dead code analysis report
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

---

## Database Schema

The application uses PostgreSQL with the `bre_` prefix for all table names, indicating integration with an existing database system.

### Table Overview

| Table Name | Drizzle Export | Purpose |
|------------|----------------|---------|
| `bre_shops` | [`shops`](src/lib/schema.ts:7) | Shop information |
| `bre_shop_account` | [`accounts`](src/lib/schema.ts:13) | Account information |
| `bre_shop_account_matrix` | [`shopAccountMatrix`](src/lib/schema.ts:19) | Many-to-many shop-account relationships |
| `bre_account_index` | [`accountIndex`](src/lib/schema.ts:25) | File-to-account links (DEPRECATED) |
| `bre_shops_index` | [`shopsIndex`](src/lib/schema.ts:31) | File-to-shop links (DEPRECATED) |
| `bre_advance_index` | [`advanceIndex`](src/lib/schema.ts:37) | File metadata (name, preview URL) |
| `bre_display_names` | [`displayName`](src/lib/schema.ts:44) | Tag/display name definitions |
| `bre_display_name_index` | [`displayNameMatrix`](src/lib/schema.ts:50) | Tag-to-entity relationships |
| `bre_file_junction` | [`fileJunction`](src/lib/schema.ts:60) | Triadic shop-file-account relationships (SOURCE OF TRUTH) |
| `bre_hashes` | *(not in Drizzle schema)* | Perceptual hash values for reverse search |
| `rag_model_settings` | [`ragModelSettings`](src/lib/schema.ts:68) | RAG model preferences |

### Schema Definitions

#### Shops Table (`bre_shops`)

```typescript
export const shops = pgTable('bre_shops', {
  shopId: bigint('shop_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  shopName: text('shop_name').notNull(),
})
```

#### Accounts Table (`bre_shop_account`)

```typescript
export const accounts = pgTable('bre_shop_account', {
  accountId: bigint('account_id', { mode: 'number' }).primaryKey().generatedByDefaultAsIdentity(),
  accountName: text('account_name').notNull(),
})
```

#### Shop-Account Matrix (`bre_shop_account_matrix`)

```typescript
export const shopAccountMatrix = pgTable('bre_shop_account_matrix', {
  shopId: bigint('shop_id', { mode: 'bigint' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'bigint' }).references(() => accounts.accountId),
})
```

#### File-Junction Table (`bre_file_junction`)

The central triadic relationship table that stores all shop-file-account relationships. This is the **source of truth** for all file linking operations.

```typescript
export const fileJunction = pgTable('bre_file_junction', {
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  fileId: text('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
  published: boolean('published').default(false),
})
```

**Usage Notes:**
- All file linking operations (`link-to-shop-account`, `unlink`, `published`) use this table
- The `linked-files-search` endpoint queries this table as the source of truth
- ON CONFLICT DO NOTHING prevents duplicate entries during linking
- Composite relationship: a file can be linked to the same shop multiple times via different accounts

#### Advance Index (`bre_advance_index`)

```typescript
export const advanceIndex = pgTable('bre_advance_index', {
  fileId: integer('fileid').primaryKey().generatedAlwaysAsIdentity(),
  name: text('name').notNull(),
  previewUrl: text('preview_url'),
})
```

#### Display Names (`bre_display_names`)

```typescript
export const displayName = pgTable('bre_display_names', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).primaryKey(),
  displayName: text('display_name').notNull(),
})
```

#### Display Name Matrix (`bre_display_name_index`)

```typescript
export const displayNameMatrix = pgTable('bre_display_name_index', {
  displayNameId: bigint('display_name_id', { mode: 'number' }).references(() => displayName.displayNameId),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
  fileId: text('file_id'),
})
```

#### RAG Model Settings (`rag_model_settings`)

```typescript
export const ragModelSettings = pgTable('rag_model_settings', {
  id: serial('id').primaryKey(),
  key: text('key').notNull().unique(),
  value: text('value').notNull(),
  description: text('description'),
  updatedAt: text('updated_at'),
})
```

---

## API Reference

### Shops API

#### GET `/api/shops`

List all shops with account and file counts.

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

#### POST `/api/shops`

Create a new shop.

**Request Body:**
```json
{ "shopName": "New Shop" }
```

**Implementation:** [`src/server/api/shops/index.post.ts`](src/server/api/shops/index.post.ts)

#### PUT `/api/shops/:id`

Update an existing shop's name.

**Request Body:**
```json
{ "shopName": "Updated Shop Name" }
```

**Implementation:** [`src/server/api/shops/[id].put.ts`](src/server/api/shops/[id].put.ts)

#### DELETE `/api/shops/:id`

Delete a shop and unlink all associated accounts.

**Implementation:** [`src/server/api/shops/[id].delete.ts`](src/server/api/shops/[id].delete.ts)

### Shop Accounts API

#### GET `/api/shops/:id/accounts`

List all accounts linked to a specific shop.

**Implementation:** [`src/server/api/shops/[id]/accounts.get.ts`](src/server/api/shops/[id]/accounts.get.ts)

#### POST `/api/shops/:id/accounts`

Link an account to a shop.

**Request Body:**
```json
{ "accountId": 1 }
```

**Implementation:** [`src/server/api/shops/[id]/accounts.post.ts`](src/server/api/shops/[id]/accounts.post.ts)

#### DELETE `/api/shops/:id/accounts`

Unlink an account from a shop.

**Request Body:**
```json
{ "accountId": 1 }
```

**Implementation:** [`src/server/api/shops/[id]/accounts.delete.ts`](src/server/api/shops/[id]/accounts.delete.ts)

#### GET `/api/shops/:id/accounts-with-files`

List accounts linked to a shop with file counts filtered by shop.

**Response:**
```json
[
  {
    "account_id": 1,
    "account_name": "Artist Account",
    "fileCount": 42,
    "publishedCount": 35,
    "unpublishedCount": 7
  }
]
```

**Implementation:** [`src/server/api/shops/[id]/accounts-with-files.get.ts`](src/server/api/shops/[id]/accounts-with-files.get.ts)

### Files API

#### GET `/api/files/browse-all`

Browse all files with pagination and sorting.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 48 | Results per page |
| `offset` | integer | 0 | Pagination offset |
| `sortBy` | string | fileid | Sort field |
| `sortOrder` | string | asc | Sort direction |

**Implementation:** [`src/server/api/files/browse-all.get.ts`](src/server/api/files/browse-all.get.ts)

#### GET `/api/files/search-by-name`

Search files by filename or display name.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search term |
| `shopId` | string | Yes | Shop ID filter |
| `accountId` | string | No | Account ID filter |

**Implementation:** [`src/server/api/files/search-by-name.get.ts`](src/server/api/files/search-by-name.get.ts)

#### POST `/api/files/link-to-shop-account`

Link a file to a shop and account.

**Request Body:**
```json
{
  "fileId": 123,
  "shopId": 1,
  "accountId": 5,
  "published": false,
  "displayNames": ["My Image", "Product Photo"]
}
```

**Implementation:** [`src/server/api/files/link-to-shop-account.post.ts`](src/server/api/files/link-to-shop-account.post.ts)

#### POST `/api/files/unlink`

Unlink a file from a shop/account.

**Request Body:**
```json
{ "fileId": 123, "shopId": 1, "accountId": 5 }
```

**Implementation:** [`src/server/api/files/unlink.post.ts`](src/server/api/files/unlink.post.ts)

#### PUT `/api/files/published`

Update published status for a file.

**Request Body:**
```json
{ "fileId": 123, "shopId": 1, "published": true }
```

**Implementation:** [`src/server/api/files/published.put.ts`](src/server/api/files/published.put.ts)

#### POST `/api/files/reverse-search`

Reverse image search using perceptual hashing.

**Request:** `multipart/form-data`
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | File | Yes | - | Uploaded image |
| `hashMethod` | string | No | whash | whash, ahash, or phash |

**Implementation:** [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts)

#### POST `/api/files/rag-search`

RAG semantic search proxy to Python service.

**Request Body:**
```json
{
  "query": "sunset landscape painting",
  "top_k": 24,
  "min_similarity": 0.25
}
```

**Implementation:** [`src/server/api/files/rag-search.post.ts`](src/server/api/files/rag-search.post.ts)

### Linked Files Search

#### GET `/api/shops/:id/linked-files-search`

Advanced linked file search with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | - | Search term |
| `accountId` | string | - | Account filter |
| `limit` | integer | 15 | Results per page |
| `offset` | integer | 0 | Pagination offset |
| `published` | string | - | Filter: true, false, or all |

**Response:**
```json
{
  "results": [
    {
      "fileId": 123,
      "filename": "image.jpg",
      "previewUrl": "/api/files/preview-proxy/123?x=540&y=540",
      "allDisplayNames": ["My Image"],
      "published": true,
      "accountIds": [5],
      "accountNames": ["Artist Account"]
    }
  ],
  "totalCount": 42
}
```

**Implementation:** [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts)

### Settings API (RAG)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings/rag-models` | GET | List available RAG models |
| `/api/settings/rag-model/current` | GET | Get current model |
| `/api/settings/rag-model` | POST | Switch model |
| `/api/settings/rag-model/download` | POST | Download model |
| `/api/settings/rag-cache/evict` | POST | Evict cache |
| `/api/settings/rag-cache-config` | GET/POST | Get/update cache config |
| `/api/settings/rag-index/rebuild` | POST | Rebuild TF-IDF index |

---

## Composables

### useShops()

Manages shop CRUD operations.

```typescript
const { shops, loading, error, fetchShops, createShop } = useShops()
```

**Returns:**
| Property | Type | Description |
|----------|------|-------------|
| `shops` | `Ref<Shop[]>` | List of shops |
| `loading` | `Ref<boolean>` | Loading state |
| `error` | `Ref<string\|null>` | Error message |
| `fetchShops` | `Function` | Fetch shops from API |
| `createShop` | `Function` | Create new shop |

### useLinkedFiles()

Manages linked files browsing (Shop -> Account -> Files hierarchy).

```typescript
const {
  selectedShop, selectedAccount, linkedFiles, offset, limit,
  searchQuery, publishedFilter, fetchAccounts, fetchFiles,
  unlinkFile, togglePublished, updateDisplayNames
} = useLinkedFiles()
```

**Key Methods:**
| Method | Parameters | Description |
|--------|------------|-------------|
| `fetchAccounts` | `shopId: number` | Fetch accounts for shop |
| `fetchFiles` | - | Fetch linked files with pagination |
| `setShop` | `shop` | Set selected shop |
| `setAccount` | `account` | Set selected account |
| `unlinkFile` | `fileId, shopId, accountId` | Unlink file |
| `togglePublished` | `fileId, newPublished` | Toggle published status |
| `updateDisplayNames` | `fileId, newNames` | Update display names |

### useLinkFiles()

Manages file linking operations including name search and reverse image search.

```typescript
const {
  searchMode, searchQuery, searchResults, linkFileToShopAccount,
  searchByFilename, reverseSearchImage
} = useLinkFiles()
```

### useImagePreview()

Manages image preview modal state.

```typescript
const { open, close, navigate, state } = useImagePreview()
```

**State:**
```typescript
{
  isOpen: boolean,
  currentImage: PreviewImage | null,
  images: PreviewImage[]
}
```

### useRagSearch()

Manages RAG semantic search.

```typescript
const {
  query, topK, minSimilarity, offset, results, hasMore,
  search, loadMore, clearResults
} = useRagSearch()
```

### useRAGSettings()

Manages RAG settings (model selection, cache config, index rebuild).

```typescript
const {
  currentModel, cacheConfig, availableModels,
  switchModel, downloadModel, updateCacheConfig, rebuildIndex
} = useRAGSettings()
```

### useTheme()

Manages light/dark theme toggle.

```typescript
const { theme, toggleTheme } = useTheme()
```

---

## Pages

### `/` - Home ([`src/pages/index.vue`](src/pages/index.vue))

Redirects to `/shops`. Shows loading spinner during redirect.

### `/shops` - Shops & Accounts ([`src/pages/shops.vue`](src/pages/shops.vue))

Full shop and account management interface:
- Shop list with account/file counts
- Create/update/delete shops
- Account management within shop context
- Link/unlink accounts to shops

### `/files` - File Search ([`src/pages/files.vue`](src/pages/files.vue))

Consolidated file search page with four modes:

| Tab | Search Mode | API Endpoint |
|-----|-------------|--------------|
| Semantic | RAG natural language search | `/api/files/rag-search` |
| Name | Text search by filename/display name | `/api/files/search-by-name` |
| Browse All | Paginated file browser | `/api/files/browse-all` |
| Reverse | Perceptual hash image search | `/api/files/reverse-search` |

**Features:**
- Image preview modal with navigation
- File linking to shops/accounts
- Display name management
- Published status toggle
- Infinite scroll for search results

### `/linked-files` - Linked Files Browser ([`src/pages/linked-files.vue`](src/pages/linked-files.vue))

Hierarchical file browser:
- Shop selection (dropdown)
- Account selection with file counts
- File table with pagination
- Published/unpublished filtering
- Search within selected shop+account
- Inline display name editing
- Published status toggle

### `/settings` - Settings ([`src/pages/settings.vue`](src/pages/settings.vue))

Application settings:
- Theme toggle (light/dark)
- RAG model management (switch, download)
- Cache configuration
- TF-IDF index rebuild

### `/performance` - Performance ([`src/pages/performance.vue`](src/pages/performance.vue))

Placeholder page for future performance monitoring features.

---

## Components

### ImagePreviewModal ([`src/components/ImagePreviewModal.vue`](src/components/ImagePreviewModal.vue))

Modal component for previewing images with navigation.

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `isOpen` | `boolean` | Modal visibility |
| `currentImage` | `PreviewImage\|null` | Current image |
| `images` | `PreviewImage[]` | All images for navigation |

**Events:**
| Event | Payload | Description |
|-------|---------|-------------|
| `close` | - | Close modal |
| `navigate` | `{ direction: 'prev'\|'next' }` | Navigate images |

---

## Types

### Shop ([`src/types/shop.ts`](src/types/shop.ts))

```typescript
export interface Shop {
  shop_id: number
  shop_name: string
  account_count?: number
  file_count?: number
}

export interface ShopWithAccounts extends Shop {
  accounts?: Account[]
}
```

### Account ([`src/types/account.ts`](src/types/account.ts))

```typescript
export interface Account {
  account_id: number
  account_name: string
}
```

### LinkedFileResult ([`src/types/linkedFile.ts`](src/types/linkedFile.ts))

```typescript
export interface LinkedFileResult {
  fileId: number | bigint
  filename: string
  previewUrl: string
  allDisplayNames: string[]
  published: boolean
  accountId: number | bigint
  accountIds: (number | bigint)[]
  accountNames: string[]
}
```

### LinkFileResult ([`src/types/linkFiles.ts`](src/types/linkFiles.ts))

```typescript
export interface LinkFileResult {
  fileId: number | bigint
  filename: string
  previewUrl: string
  accountId: number | bigint
  accountName: string
}

export type HashMethod = 'whash' | 'ahash' | 'phash'
export type SearchMode = 'filename' | 'reverse'
```

---

## Python Services

### RAG Search Service ([`src/py-code/rag_search/`](src/py-code/rag_search/))

FastAPI service providing semantic search using embedding models and TF-IDF.

**Key Components:**
| File | Purpose |
|------|---------|
| `main.py` | FastAPI application with API endpoints |
| `search.py` | Core search logic (TF-IDF weighted embeddings) |
| `database.py` | Database connection and query handler |
| `model_loader.py` | Embedding model loading and LRU caching |
| `config.py` | RAG configuration |
| `tfidf_index.py` | TF-IDF vectorization and index persistence |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rag/search` | POST | Semantic search |
| `/api/v1/rag/models` | GET | List available models |
| `/api/v1/rag/models/current` | GET | Get current model |
| `/api/v1/rag/models/switch` | POST | Switch model |
| `/api/v1/rag/models/download` | POST | Download model |
| `/api/v1/rag/cache/config` | GET/POST | Cache configuration |
| `/api/v1/rag/cache/evict` | POST | Evict cache |
| `/api/v1/rag/index/rebuild` | POST | Rebuild TF-IDF index |
| `/api/v1/rag/health` | GET | Health check |

### Hash Calculation Service ([`src/py-code/hash_calc/`](src/py-code/hash_calc/))

FastAPI service for perceptual hash calculation.

**Hash Types:**
| Type | Description | Use Case |
|------|-------------|----------|
| `whash` (Wavelet) | Sensitive to structural changes | General similarity |
| `ahash` (Average) | Sensitive to brightness | Brightness-invariant matching |
| `phash` (Perceptual) | Sensitive to frequency domain | Frequency-based matching |

---

## Development

### Prerequisites

- Node.js 20+
- PostgreSQL 16+
- Python 3.x (for RAG and hash services)
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

```bash
docker-compose up
# Access at http://localhost:3000
docker-compose down
```

---

## Deployment

### Docker Production Build

```bash
docker build --build-arg DB_HOST=your-db-host -t shop-management .
docker run -p 3000:3000 \
  -e DB_PASSWORD=your-password \
  -e NC_ACC=your-nc-user \
  -e NC_PASS=your-nc-pass \
  shop-management
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `shop_management` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `NC_HOST` | `localhost` | Nextcloud host |
| `NC_ACC` | - | Nextcloud username |
| `NC_PASS` | - | Nextcloud password |

---

## Dead Code & Deprecations

### Files Referenced in Documentation But Missing

| File | Status | Action |
|------|--------|--------|
| `src/pages/link-files.vue` | Never existed | Remove from docs |
| `src/pages/browse.vue` | Never existed | Remove from docs |

### Unused Type Exports

| File | Status | Action |
|------|--------|--------|
| `src/types/file.ts` | Exported but never imported | Can be safely removed |

### Deprecated Database Tables

| Table | Status | Notes |
|-------|--------|-------|
| `bre_account_index` | Deprecated | Still used by some endpoints, replaced by `bre_file_junction` |
| `bre_shops_index` | Deprecated | Still used by some endpoints, replaced by `bre_file_junction` |

**Note:** These tables are still actively queried by several API endpoints. A full migration would require updating all queries to use `bre_file_junction`. See [`DEAD_CODE_ANALYSIS.md`](DEAD_CODE_ANALYSIS.md) for details.

### Placeholder Pages

| Page | Status |
|------|--------|
| `src/pages/performance.vue` | Empty placeholder for future features |

### Git History Summary

Key commits affecting the current codebase:

| Commit | Message | Impact |
|--------|---------|--------|
| `aaaee84` | Merge PR #12 - Typescript conversion | Major restructuring |
| `a11f37f` | Fixed reverse search fatal flaw | Critical bug fix |
| `fc7998a` | Cleanup time! | Removed unnecessary files |
| `15c5740` | Typescript App combining all POCs | Consolidated functionality |
| `4033bbc` | Added display names linking, unlinking & editing | New feature |
| `ccf3682` | Fixed orphaned display names deletion | Bug fix |

For a complete dead code analysis, see [`DEAD_CODE_ANALYSIS.md`](DEAD_CODE_ANALYSIS.md).
