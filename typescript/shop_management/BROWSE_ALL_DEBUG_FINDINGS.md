# Browse All Debug Findings

## Issue Description
The "Browse All" feature loads a couple of batches but then stops loading files before reaching all 1517 files in the database.

## Database Verification
- Total files in `bre_advance_index`: **1517**
- File IDs range from ~1000 to ~9999
- Data appears valid with proper `fileid`, `name`, and `preview_url` fields

## Potential Root Causes Analyzed

| # | Cause | Likelihood | Status |
|---|-------|------------|--------|
| 1 | IntersectionObserver not triggering after initial load | High | Pending validation |
| 2 | browseHasMore set to false prematurely (API returns < 48) | High | Pending validation |
| 3 | Network errors silently caught | Medium | Pending validation |
| 4 | DISTINCT ON + OFFSET pagination issue | Medium | Pending validation |
| 5 | New PostgreSQL Pool per request causing connection issues | Low | Pending validation |
| 6 | Race condition in loadMoreFiles | Low | Pending validation |
| 7 | watcher + nextTick timing issue | Low | Pending validation |

## Top 2 Most Likely Causes

### Cause #1: IntersectionObserver not triggering
- Location: files.vue
- The sentinel element may not be detected as visible due to:
  - CSS layout issues
  - Insufficient `rootMargin` (currently 200px)
  - Page not being scrollable after content renders

### Cause #2: browseHasMore set to false prematurely
- Location: files.vue
- If API returns fewer than 48 results for any reason, `browseHasMore` becomes `false`
- Once false, infinite scroll stops permanently

## Diagnostic Logging Added

### Backend (browse-all.get.ts)
- Logs request parameters: `limit`, `offset`, `sortBy`, `sortOrder`
- Logs response: `rowsReturned`, `hasMore`
- Warns if returned rows < limit (will stop infinite scroll)

### Frontend (browse.vue) - TO BE ADDED
- Logs when `fetchBrowseFiles` / `loadMoreFiles` is called
- Logs when IntersectionObserver callback fires
- Logs `browseHasMore` state changes
- Logs number of results received

## Test Results
_TO BE FILLED AFTER TESTING_

## Final Root Cause
_TO BE FILLED AFTER DIAGNOSTICS_

## Fix Applied
_TO BE FILLED AFTER FIX_
