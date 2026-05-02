# Unused Code Cleanup - Post-Unified Files Tab

> Generated: 2026-05-01
> Reason: Unified `link-files.vue` and `browse.vue` into single `files.vue`

## Files to DELETE

### Pages (replaced by unified `files.vue`)
| File | Lines | Reason |
|------|-------|--------|
| `src/pages/browse.vue` | 688 | Replaced by unified `files.vue` (semantic + name + browse_all modes) |
| `src/pages/link-files.vue` | 607 | Replaced by unified `files.vue` (name + reverse modes + linking) |

### Backup
| File | Lines | Reason |
|------|-------|--------|
| `src/pages/files.vue.bak` | ~400 | Old backup of files.vue before unification |

### Composables (partially unused after unification)
| File | Lines | Unused Functions | Notes |
|------|-------|------------------|-------|
| `src/composables/useLinkedFiles.ts` | 346 | ALL | Entire composable is unused. It was used by the OLD `files.vue` (linked files page with shop/account tree view). The new unified `files.vue` uses `useLinkFiles` instead. |

### Types (check if used elsewhere)
| File | Lines | Content | Status |
|------|-------|---------|--------|
| `src/types/linkedFile.ts` | ~20 | LinkedFile interface | Check usage - may be unused |

### Navigation (updated)
| File | Change |
|------|--------|
| `src/layouts/default.vue` | Removed `/link-files` and `/browse` links. Renamed `/files` from "Linked Files" to "Files" |

## Functions/Features MOVED to Unified Tab

The following functionality was merged from old pages into `files.vue`:

| Source | Functionality |
|--------|---------------|
| `browse.vue` | Semantic search (RAG), Name search, Browse all (paginated), Grid layout, Image preview |
| `link-files.vue` | Name search, Reverse image search, Linking sidebar menu, Shop/Account selection |

## Composables Still in Use

| Composable | Used By | Status |
|------------|---------|--------|
| `useRagSearch.ts` | `files.vue` | ACTIVE |
| `useLinkFiles.ts` | `files.vue` | ACTIVE |
| `useImagePreview.ts` | `files.vue` | ACTIVE |
| `useLinkedFiles.ts` | NONE | **DELETABLE** |
| `useShops.ts` | `shops.vue` | ACTIVE |
| `useTheme.ts` | Multiple | ACTIVE |
| `useRAGSettings.ts` | `settings.vue` | ACTIVE |

## API Endpoints Status

| Endpoint | Used By | Status |
|----------|---------|--------|
| `/api/files/rag-search.post.ts` | `files.vue` | ACTIVE |
| `/api/files/search-by-name.get.ts` | `files.vue` | ACTIVE |
| `/api/files/browse-all.get.ts` | `files.vue` | ACTIVE |
| `/api/files/reverse-search.post.ts` | `files.vue` | ACTIVE |
| `/api/files/link-to-shop-account.post.ts` | `files.vue` | ACTIVE |
| `/api/files/unlink.post.ts` | `shops.vue` (linked files) | ACTIVE |
| `/api/files/published.put.ts` | `shops.vue` (linked files) | ACTIVE |
| `/api/files/index.get.ts` | ? | CHECK USAGE |
| `/api/files/index.post.ts` | ? | CHECK USAGE |
| `/api/files/[fileId]/tags.get.ts` | ? | CHECK USAGE |
| `/api/files/preview-proxy/[fileId].get.ts` | ? | CHECK USAGE |

## Cleanup Commands

```bash
cd typescript/shop_management/src/pages
rm -f browse.vue link-files.vue files.vue.bak

cd typescript/shop_management/src/composables
rm -f useLinkedFiles.ts

# Check for linkedFile.ts usage
grep -r "linkedFile" src/ --include="*.ts" --include="*.vue"
```

## Pre-Cleanup Checklist

- [ ] Test unified `/files` page with all 4 modes (semantic, name, browse_all, reverse)
- [ ] Test linking functionality in all search modes
- [ ] Test reverse search 2x1 + 3x3 grid layout
- [ ] Verify `/shops` page still works (uses useLinkedFiles? check!)
- [ ] Verify navigation works correctly

## IMPORTANT

DO NOT delete until testing is complete and verified!
