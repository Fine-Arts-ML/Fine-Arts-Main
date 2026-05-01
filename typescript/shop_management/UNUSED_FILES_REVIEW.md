# Potentially Unused Files and Code - Review Flag

This document flags files and code sections that may be unused or dead code. **Do not delete** without thorough review, as some may be used in ways not immediately visible (e.g., imported by dynamically loaded modules, referenced in configuration, or used by the Python backend).

---

## 1. Skeleton/Placeholder Pages

These pages have minimal or no functional implementation:

### [`src/pages/performance.vue`](src/pages/performance.vue)
**Status:** Skeleton page - nearly empty template

```vue
<script setup lang="ts">
import { ref } from 'vue'
const activeFileTab = ref('overview')
</script>

<template>
  <div class="p-6">
    <!-- Empty -->
  </div>
</template>
```

**References:**
- Linked in sidebar navigation (`src/layouts/default.vue:133-140`)
- No actual functionality implemented

**Recommendation:** Either implement the performance monitoring feature or remove the page and navigation link if the feature is deprecated.

---

### [`src/pages/browse.vue`](src/pages/browse.vue)
**Status:** Skeleton page - tab structure only with RAG search integration

```vue
<script setup lang="ts">
import { useRagSearch, type SearchResult } from '~/composables/useRagSearch'
import { useLinkFiles } from '~/composables/useLinkFiles'
import { useImagePreview } from '~/composables/useImagePreview'

// RAG search state
const { search: ragSearch, clearResults: clearRagResults } = useRagSearch()
const ragResults = ref<SearchResult[]>([])
</script>
```

**References:**
- Linked in sidebar navigation (`src/layouts/default.vue:122-129`)
- Uses `Tabs` component from `radix-vue` but no tab content is rendered
- Tab values (`browse_all`, `by_shop`, `by_acc`) don't match the `TABS` constant in `src/lib/constants.ts` (`OVERVIEW`, `ADD_FILES`, etc.)
- Integrates with `useRagSearch` composable but results are not displayed

**Recommendation:** Either implement the browse functionality or remove the page and navigation link.

---

## 2. Potentially Unused Type Exports

### [`src/types/index.ts`](src/types/index.ts)
**Status:** Exports types that may not be widely used

```typescript
export type { Shop, ShopFormData, ShopWithAccounts } from './shop'
export type { Account, AccountFormData, ShopAccountLink } from './account'
export type { File, FileSearchResult, FileFormData, ImageSearchData } from './file'
```

**Potentially Unused Types:**
| Type | File | Usage Found |
|------|------|-------------|
| `ShopFormData` | `shop.ts` | Not found in any import |
| `ShopWithAccounts` | `shop.ts` | Not found in any import |
| `AccountFormData` | `account.ts` | Not found in any import |
| `ShopAccountLink` | `account.ts` | Not found in any import |
| `File` | `file.ts` | Not found in any import |
| `FileSearchResult` | `file.ts` | Not found in any import |
| `FileFormData` | `file.ts` | Not found in any import |
| `ImageSearchData` | `file.ts` | Not found in any import |

**Note:** The types in `linkedFile.ts` and `linkFiles.ts` ARE actively used by composables and pages.

**Recommendation:** Verify if these types are used anywhere. If not, consider removing them or documenting their intended purpose.

---

## 3. Potentially Unused Constants

### [`src/lib/constants.ts`](src/lib/constants.ts)
**Status:** Some constants may not be referenced

| Constant | Value | Usage Found |
|----------|-------|-------------|
| `IMAGE_RESIZE_CONFIG` | `{ SMALL, MEDIUM, LARGE }` | NOT found in any import |
| `DEFAULT_BATCH_SIZE` | `20` | NOT found in any import |
| `MAX_BATCH_SIZE` | `100` | NOT found in any import |
| `TABS` | `{ SHOPS, ACCOUNTS, PERFORMANCE, OVERVIEW, ADD_FILES }` | NOT found in any import |

**Note:** `HASH_TYPES` IS used (implicitly via the `HashMethod` type).

**Recommendation:** Verify if these constants are used. The `TABS` constant values don't match the actual tab values used in `browse.vue` (`browse_all`, `by_shop`, `by_acc`), suggesting the constant may be outdated.

---

## 4. Unused Client-Side Utility Functions

### [`src/lib/utils.ts`](src/lib/utils.ts:8-39)
**Status:** Multiple utility functions exist but are not imported anywhere

| Function | Purpose | Usage Found |
|----------|---------|-------------|
| `formatFileSize(bytes)` | Format bytes to human-readable string | NOT found in any import |
| `truncateString(str, maxLength)` | Truncate string with ellipsis | NOT found in any import |
| `generateId()` | Generate random string ID | NOT found in any import |
| `transformPreviewUrl(previewUrl, size)` | Transform preview URL to absolute Nextcloud URL (client-side) | NOT found in any import |

**Note:** The server-side [`transformPreviewUrl()`](src/server/utils/preview.ts) IS actively used by all file search API routes. The client-side version is dead code.

**Recommendation:** Remove these unused functions or document their intended purpose.

---

## 5. Diagnostic Code in Production

### [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts)
**Status:** Contains diagnostic/debug code that should be reviewed

```typescript
// DIAGNOSTIC: Compare with Streamlit-style query (without bre_shops_index filter)
const streamlitQuery = `...`
const streamlitResult = await pool.query(streamlitQuery, [shopId])
const streamlitRows = (streamlitResult as any).rows
console.log(`[linked-files-search] Streamlit-style query result count:`, streamlitRows.length)
console.log(`[linked-files-search] Missing files (in Streamlit but not TS):`, streamlitRows.length - rows.length)
```

**Impact:**
- Executes an **additional** database query on every call
- Adds unnecessary latency to the API response
- Logs sensitive data structure information

**Recommendation:** Remove or gate behind an environment variable (e.g., `DEBUG=true`) before production deployment.

---

## 6. Console.log Statements Throughout

Multiple API routes contain extensive `console.log` statements for debugging:

| File | Log Statements |
|------|----------------|
| [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts) | 10+ log statements |
| [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts) | 15+ log statements |
| [`src/server/api/files/preview-proxy/[fileId].get.ts`](src/server/api/files/preview-proxy/[fileId].get.ts) | 1 log statement |
| [`src/composables/useLinkedFiles.ts`](src/composables/useLinkedFiles.ts) | 2 log statements |

**Recommendation:** Consider using a proper logging library with log levels (debug, info, warn, error) and gating debug logs behind an environment variable.

---

## 7. Missing CSS File

### [`src/assets/css/global.css`](src/assets/css/global.css)
**Status:** Imports non-existent `tree-view.css`

```css
@import './tree-view.css';
```

**Analysis:**
- The file `src/assets/css/tree-view.css` is referenced in the documentation's project structure but does NOT exist
- This import will cause a build warning/error

**Recommendation:** Either create `tree-view.css` with the tree view theme variables documented in DOCUMENTATION.md, or remove the import.

---

## 8. Drizzle Schema vs Raw SQL Discrepancy

### `bre_hashes` Table
**Status:** Table used in queries but NOT defined in Drizzle schema

The `bre_hashes` table is queried extensively in [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts:188-201) but is not defined in [`src/lib/schema.ts`](src/lib/schema.ts):

```sql
SELECT h.id, h.w_hash, h.a_hash, h.p_hash
FROM bre_hashes h
...
```

**Impact:**
- Drizzle ORM cannot provide type safety for this table
- Schema migrations via Drizzle won't manage this table
- Risk of schema drift

**Recommendation:** Add the `bre_hashes` table to the Drizzle schema for consistency, or document why it's excluded (e.g., managed by external system).

---

## 9. Duplicate Database Connection Pools

### Multiple Raw `pg.Pool` Instances
**Status:** Each raw SQL API route creates its own connection pool

| File | Pool Creation |
|------|---------------|
| [`src/server/api/files/search-by-name.get.ts`](src/server/api/files/search-by-name.get.ts:24-30) | New pool per request |
| [`src/server/api/files/link-to-shop-account.post.ts`](src/server/api/files/link-to-shop-account.post.ts:26-32) | New pool per request |
| [`src/server/api/files/reverse-search.post.ts`](src/server/api/files/reverse-search.post.ts:170-176) | New pool per request |
| [`src/server/api/shops/[id]/linked-files-search.get.ts`](src/server/api/shops/[id]/linked-files-search.get.ts:109-115) | New pool per request |

**Note:** The shared pool in [`src/lib/db.ts`](src/lib/db.ts) uses Drizzle ORM and is NOT reused by these routes.

**Impact:**
- Each API request creates a new connection pool (and destroys it at the end)
- This is highly inefficient and can lead to connection exhaustion under load
- The `pool.end()` calls in `finally` blocks help, but pool creation overhead remains

**Recommendation:** Create a shared raw `pg.Pool` instance (similar to `src/lib/db.ts`) and reuse it across all routes.

---

## 10. Python hash_helper.py Not Used by RAG Search

### [`src/py-code/hash_helper.py`](src/py-code/hash_helper.py)
**Status:** Used only by reverse image search, not by RAG search

The Python hash helper is used exclusively by the reverse image search feature (`src/server/api/files/reverse-search.post.ts`). It is NOT used by the RAG search system, which has its own separate Python service at `src/py-code/rag_search/`.

**Recommendation:** No action needed - this is intentional separation of concerns.

---

## 11. RAG Documentation

A separate comprehensive RAG documentation file has been created: [`DOCUMENTATION_RAG.md`](DOCUMENTATION_RAG.md)

This file documents:
- RAG architecture and data flow
- Python RAG service components
- API endpoints and request/response formats
- Search algorithm details
- Model management and caching
- TF-IDF index building
- Vue composables (useRagSearch, useRAGSettings)
- Environment variables and deployment

---

## Summary Table

| Category | File/Code | Severity | Action |
|----------|-----------|----------|--------|
| Skeleton Page | `src/pages/performance.vue` | Medium | Implement or remove |
| Skeleton Page | `src/pages/browse.vue` | Medium | Implement or remove |
| Unused Types | `src/types/index.ts` exports | Low | Verify and clean up |
| Unused Constants | `src/lib/constants.ts` | Low | Verify and clean up |
| Dead Code | `formatFileSize`, `truncateString`, `generateId` in `utils.ts` | Low | Remove if unused |
| Dead Code | `transformPreviewUrl` in `utils.ts` (client-side) | Low | Remove if unused |
| Diagnostic Code | `linked-files-search.get.ts` | Medium | Remove or gate |
| Console Logs | Multiple files | Low | Use proper logging |
| Missing CSS | `tree-view.css` import | High | Verify file exists |
| Schema Gap | `bre_hashes` table | Medium | Add to schema |
| Connection Pools | Multiple raw SQL routes | High | Share pool instance |

---

## Review Checklist

- [ ] Verify `tree-view.css` exists or remove import
- [ ] Implement or remove `performance.vue` and `browse.vue`
- [ ] Clean up unused type exports in `src/types/index.ts`
- [ ] Clean up unused constants in `src/lib/constants.ts`
- [ ] Remove unused utility functions from `src/lib/utils.ts`
- [ ] Remove client-side `transformPreviewUrl` if unused
- [ ] Remove or gate diagnostic code in `linked-files-search.get.ts`
- [ ] Implement proper logging system
- [ ] Add `bre_hashes` to Drizzle schema
- [ ] Create shared raw `pg.Pool` instance
- [ ] Review RAG documentation in `DOCUMENTATION_RAG.md`
