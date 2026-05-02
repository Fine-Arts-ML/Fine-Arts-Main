# Unified Files Tab - Implementation Plan

## Current State Analysis

### Existing Pages
1. **browse.vue** - "Browse Files" tab
   - Modes: Semantic Search, Name Search, Browse All
   - Uses: useRagSearch composable, useLinkFiles composable
   - Features: RAG semantic search, filename search, infinite scroll browse
   - NO linking capability

2. **link-files.vue** - "Link Files" tab
   - Modes: Filename Search, Reverse Image Search
   - Uses: useLinkFiles composable, useImagePreview composable
   - Features: Filename search, reverse image search with hash matching, link-to-shop-account sidebar menu
   - Has linking capability

3. **files.vue** - "Linked Files" tab
   - Shows files already linked to shops/accounts
   - Uses: useLinkedFiles composable
   - Features: Shop drill-down, account drill-down, search, published filter, unlink
   - NO search/new file discovery

### Database Schema (Key Tables)
- `bre_advance_index` - File metadata (fileid, name, preview_url)
- `bre_file_junction` - Triadic relationship (shop_id, file_id, account_id, published)
- `bre_shop_account` - Accounts (account_id, account_name)
- `bre_shops` - Shops (shop_id, shop_name, shop_url)
- `bre_display_names` - Display names (display_name_id, display_name)
- `bre_display_name_index` - Display name mappings (display_name_id, shop_id, account_id, file_id)
- `bre_hashes` - Image hashes (id, w_hash, a_hash, p_hash)

### Existing API Endpoints
- `/api/files/rag-search` - RAG semantic search (POST)
- `/api/files/search-by-name` - Filename search (GET)
- `/api/files/browse-all` - Browse all files with pagination (GET)
- `/api/files/reverse-search` - Reverse image search (POST)
- `/api/files/link-to-shop-account` - Link file to shop+account (POST)
- `/api/files/unlink` - Unlink file from shop+account (POST)
- `/api/files/preview-proxy/[fileId]` - Preview image proxy (GET)
- `/api/shops/[id]/linked-files-search` - Search linked files (GET)

### Existing Composables
- `useRagSearch` - RAG search state and logic
- `useLinkFiles` - Filename search, reverse search, linking logic
- `useLinkedFiles` - Linked files browsing with shop/account drill-down
- `useImagePreview` - Image preview modal state

## Unified Tab Design

### New Page: `pages/files.vue` (replaces all three)

#### Tab/Mode Structure
```
┌─────────────────────────────────────────────────┐
│  Files                                          │
├─────────────────────────────────────────────────┤
│  [Semantic Search] [Name Search] [Browse All]   │
│                              [Reverse Search]   │
├─────────────────────────────────────────────────┤
│  [Search Input Area based on active mode]       │
├─────────────────────────────────────────────────┤
│  [Results Grid / Linked Files List]             │
│  [Each item has: thumbnail, name, link button]  │
└─────────────────────────────────────────────────┘
```

#### Mode Switcher (4 modes)
1. **Semantic Search** - RAG-based natural language search
2. **Name Search** - Filename/display name search
3. **Browse All** - Paginated file browser with filter + sort
4. **Reverse Search** - Image upload with hash-based similarity search

#### Unified Features
- All search modes support linking files to shops/accounts via sidebar menu
- Consistent image preview modal (1080px enlarged)
- Browse All styling (grid layout, filter, sort)
- Link Files styling (sidebar menu for linking)

#### Reverse Search Layout (Special)
```
┌──────────────┬──────────────────────────┐
│ Uploaded     │ Lowest Distance Result   │  ← 2x1 Grid (1 row)
│ Image        │ (enlarged preview)       │
├──────────────┴──────────────────────────┤
│  Other 9 Results in 3x3 Grid            │  ← 3x3 Grid
└─────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Create new unified `files.vue`
- Reuse existing composables: useRagSearch, useLinkFiles, useImagePreview
- Implement mode switcher with 4 modes
- Implement shared sidebar link menu (from link-files.vue)
- Implement grid results layout (from browse.vue)
- Implement reverse search 2x1 + 3x3 layout

### Step 2: Update routing
- Remove browse.vue
- Remove link-files.vue
- Keep files.vue as the unified "Files" page

### Step 3: Update navigation
- Update layout navigation links

### Step 4: Create cleanup documentation
- Document unused code in .md file

## Code Reuse Strategy

| Feature | Source | Target |
|---------|--------|--------|
| RAG search | useRagSearch | files.vue |
| Filename search | useLinkFiles.searchByFilename | files.vue |
| Reverse search | useLinkFiles.reverseSearch | files.vue |
| Linking logic | useLinkFiles.linkFileToShopAccount | files.vue |
| Shop/account selection | useLinkFiles shops/accounts | files.vue |
| Sidebar link menu | link-files.vue template | files.vue |
| Grid layout | browse.vue template | files.vue |
| Image preview | useImagePreview | files.vue |
| Browse All API | browse-all.get.ts | files.vue |
| Preview proxy | preview-proxy/[fileId].get.ts | files.vue |

## Files to Delete After Testing
- `pages/browse.vue`
- `pages/link-files.vue`
- `composables/useLinkedFiles.ts` (if no longer needed by other pages)
- `pages/files.vue` (old version - backed up)
- `composables/useLinkFiles.ts` (logic merged into files.vue or new composable)

## Styling Decisions
- Use browse.vue grid styling (6-column responsive grid)
- Use link-files.vue sidebar menu styling for linking
- Use browse.vue toolbar styling for filter/sort in Browse All mode
