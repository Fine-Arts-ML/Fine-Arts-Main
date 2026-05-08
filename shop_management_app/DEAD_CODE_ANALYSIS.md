# Dead Code Analysis - Shop Management Application

> Generated: 2026-05-08  
> Based on: Git history + codebase analysis

---

## Executive Summary

This document identifies code files, types, and database schema elements that are **no longer used** by the application and can potentially be safely removed. The analysis covers:

1. Files referenced in documentation but not present on disk
2. TypeScript/Vue files that are never imported
3. Python scripts that are never called
4. Database schema tables that are deprecated
5. Type exports that are unused

---

## 1. Missing Page Files (Referenced in Docs, Not on Disk)

The following pages are mentioned in [`DOCUMENTATION.md`](DOCUMENTATION.md) but **do not exist** in the filesystem:

| File | Status | Notes |
|------|--------|-------|
| `src/pages/link-files.vue` | **MISSING** | Documentation lists this as "Link files page" |
| `src/pages/browse.vue` | **MISSING** | Documentation lists this as "Browse files page (skeleton)" |

**Current Pages:**
- [`src/pages/index.vue`](src/pages/index.vue) - Redirects to `/shops`
- [`src/pages/shops.vue`](src/pages/shops.vue) - Shop & Account management
- [`src/pages/files.vue`](src/pages/files.vue) - File search & management (combines name search, reverse search, RAG search)
- [`src/pages/linked-files.vue`](src/pages/linked-files.vue) - Linked files browser
- [`src/pages/performance.vue`](src/pages/performance.vue) - Skeleton/placeholder page
- [`src/pages/settings.vue`](src/pages/settings.vue) - RAG & theme settings

**Recommendation:** Update `DOCUMENTATION.md` to remove references to `link-files.vue` and `browse.vue`. The functionality was consolidated into `files.vue` during the TypeScript conversion (commit `15c5740`).

---

## 2. Unused Type Exports

### `src/types/file.ts`

**Status:** ⚠️ **EXPORTED BUT NEVER IMPORTED**

This file is exported from [`src/types/index.ts`](src/types/index.ts:3):
```typescript
export type { File, FileSearchResult, FileFormData, ImageSearchData } from './file'
```

However, **no Vue component or composable imports these types**. The `files.vue` page imports `LinkFileResult` from `~/types/linkFiles` instead.

**Recommendation:** 
- If `File`, `FileSearchResult`, `FileFormData`, `ImageSearchData` are not used elsewhere, this file can be safely removed.
- Also remove the export from `src/types/index.ts`.

---

## 3. Unused Python Scripts

### `src/py-code/hash_helper.py`

**Status:** ⚠️ **NEVER CALLED FROM TYPESCRIPT**

This script is designed to calculate perceptual hashes (whash, ahash, phash) via stdin/stdout IPC:
```python
# Reads base64 image from stdin
# Outputs base64 JSON with whash, ahash, phash
```

However, **no TypeScript/Vue file imports or spawns this script**. The reverse image search functionality in `files.vue` uses a different approach - it calls the server API endpoint `/api/files/reverse-search.post.ts` which may use a different hash calculation method.

**Recommendation:** 
- Verify that reverse search works without this script.
- If confirmed unused, remove `src/py-code/hash_helper.py`.

---

## 4. Deprecated Database Schema Tables

### `bre_account_index` and `bre_shops_index`

**Status:** ⚠️ **DEPRECATED - REPLACED BY `bre_file_junction`**

These tables are defined in [`src/lib/schema.ts`](src/lib/schema.ts:25) and [`src/lib/schema.ts:31`]:

```typescript
// Account-File index table (DEPRECATED)
export const accountIndex = pgTable('bre_account_index', {
  fileId: integer('file_id').notNull(),
  accountId: bigint('account_id', { mode: 'number' }).references(() => accounts.accountId),
})

// Shop-File index table (DEPRECATED)
export const shopsIndex = pgTable('bre_shops_index', {
  id: text('id').primaryKey(),
  shopId: bigint('shop_id', { mode: 'number' }).references(() => shops.shopId),
})
```

**Current Usage:**
| File | Usage | Can Remove? |
|------|-------|-------------|
| `src/server/api/shops/[id]/files/search.get.ts` | Uses both tables for Drizzle queries | ❌ Still used |
| `src/server/api/accounts/[id].delete.ts` | Deletes from `accountIndex` | ❌ Still used |
| `src/server/api/files/index.post.ts` | Inserts into `shopsIndex` | ❌ Still used |
| `src/server/api/shops/[id]/accounts-with-files.get.ts` | Uses raw SQL with `bre_shops_index` | ❌ Still used |
| `src/server/api/shops/[id]/files.get.ts` | Uses raw SQL with `bre_shops_index` | ❌ Still used |

**Note:** While these tables are deprecated in favor of `bre_file_junction`, they are **still actively queried** by several API endpoints. A full migration would require:
1. Updating all raw SQL queries to use `bre_file_junction`
2. Updating Drizzle queries to use `fileJunction`
3. Data migration to copy existing relationships
4. Testing all affected endpoints

**Recommendation:** Mark as deprecated with a TODO comment. Do NOT remove until a full migration is performed.

---

## 5. Unused API Endpoints

### `src/server/api/files/index.get.ts` and `src/server/api/files/index.post.ts`

**Status:** ⚠️ **POSSIBLY UNUSED**

These endpoints exist but need verification:
- `GET /api/files` - List all files
- `POST /api/files` - Create file entry

**Recommendation:** Check if any frontend code calls these endpoints. If not, they may be legacy endpoints from the original Python app.

---

## 6. Skeleton/Placeholder Pages

### `src/pages/performance.vue`

**Status:** ℹ️ **PLACEHOLDER**

This page contains only a skeleton template with no functional code:
```vue
<script setup lang="ts">
import { ref } from 'vue'
const activeFileTab = ref('overview')
</script>

<template>
  <div class="p-6"></div>
</template>
```

**Recommendation:** Keep as placeholder for future features, or remove if the performance monitoring feature is abandoned.

---

## 7. Git History Analysis

### Key Commits Affecting Code Structure

| Commit | Message | Impact |
|--------|---------|--------|
| `aaaee84` | Merge PR #12 - Typescript conversion | Major restructuring |
| `a11f37f` | Fixed reverse search fatal flaw | Critical bug fix |
| `fc7998a` | Cleanup time! | Removed unnecessary files |
| `15c5740` | Typescript App combining all previous POCs | Consolidated functionality |
| `bd2fb01` | Added Display names, fixed link&unlink | New features |
| `d2e179a` | Added preview pictures, fixed search functions | UI improvements |

### Pre-TypeScript Era (Before `15c5740`)

Before the TypeScript conversion, the app had multiple proof-of-concept (POC) implementations:
- Streamlit apps for fingerprinting (`depreciated & testing/py-code/fingerprinting/`)
- Streamlit apps for web page search (`depreciated & testing/py-code/web-page/streamlit_app/`)
- Python shop management app (`depreciated & testing/py-code/shop_managment/`)

These are correctly placed in the `depreciated & testing/` directory and should remain there.

---

## 8. Summary of Recommended Actions

### Safe to Remove Immediately

| File/Code | Reason |
|-----------|--------|
| `src/pages/link-files.vue` reference in docs | File doesn't exist |
| `src/pages/browse.vue` reference in docs | File doesn't exist |
| `src/types/file.ts` + export | Never imported |
| `src/py-code/hash_helper.py` | Never called from TS |

### Requires Migration Before Removal

| File/Code | Reason |
|-----------|--------|
| `accountIndex` (Drizzle schema) | Still used by delete account endpoint |
| `shopsIndex` (Drizzle schema) | Still used by file search endpoints |
| `bre_account_index` table (DB) | Referenced by deprecated index tables |
| `bre_shops_index` table (DB) | Referenced by deprecated index tables |

### Keep (Placeholder)

| File/Code | Reason |
|-----------|--------|
| `src/pages/performance.vue` | Future feature placeholder |
| `depreciated & testing/` directory | Historical POC code |

---

## 9. Verification Checklist

Before removing any code, verify:

- [ ] Search for imports/references in all `.vue` and `.ts` files
- [ ] Check server API routes for `$fetch` calls to unused endpoints
- [ ] Verify Python scripts are not spawned via `child_process`
- [ ] Test database queries that reference deprecated tables
- [ ] Confirm no external tools/services depend on removed endpoints

---

## 10. File Structure Reference

### Current Active Files

```
shop_management_app/src/
├── app.vue                          # Root component
├── app.config.ts                    # App configuration
├── env.d.ts                         # Environment types
├── assets/css/
│   ├── global.css                   # Global styles + theming
│   └── tree-view.css                # Tree view styles
├── components/
│   └── ImagePreviewModal.vue        # Image preview modal
├── composables/
│   ├── useImagePreview.ts           # Image preview logic
│   ├── useLinkedFiles.ts            # Linked files browsing
│   ├── useLinkFiles.ts              # File linking (search, reverse search)
│   ├── useRagSearch.ts              # RAG semantic search
│   ├── useRAGSettings.ts            # RAG settings management
│   ├── useShops.ts                  # Shop management logic
│   └── useTheme.ts                  # Theme toggle
├── layouts/
│   └── default.vue                  # Sidebar layout
├── lib/
│   ├── constants.ts                 # App constants
│   ├── db.ts                        # Database connections
│   ├── schema.ts                    # Drizzle ORM schema
│   └── utils.ts                     # Helper utilities
├── pages/
│   ├── index.vue                    # Redirect to /shops
│   ├── shops.vue                    # Shop & Account management
│   ├── files.vue                    # File search & management
│   ├── linked-files.vue             # Linked files browser
│   ├── performance.vue              # Placeholder
│   └── settings.vue                 # Settings page
├── plugins/
│   └── theme.ts                     # Theme plugin
├── py-code/
│   ├── hash_calc/                   # Perceptual hash calculation service
│   └── rag_search/                  # RAG search FastAPI service
├── server/
│   ├── api/
│   │   ├── accounts/                # Account CRUD
│   │   ├── files/                   # File operations
│   │   ├── settings/                # RAG settings
│   │   └── shops/                   # Shop CRUD + relationships
│   └── utils/
│       └── preview.ts               # Preview URL utilities
├── types/
│   ├── index.ts                     # Type exports
│   ├── shop.ts                      # Shop types
│   ├── account.ts                   # Account types
│   ├── file.ts                      # File types (UNUSED)
│   ├── linkedFile.ts                # Linked file types
│   └── linkFiles.ts                 # Link file types
```
