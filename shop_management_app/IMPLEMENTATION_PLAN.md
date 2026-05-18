# Implementation Plan: Fix Description Count Bug & Scale Improvements

## Problem Summary

The `/tags-and-tagging/sync` page shows **63 files with descriptions** when only **2 files** actually have descriptions. The bug exists because the frontend counts mapping rows instead of distinct file IDs. At scale (4,500+ descriptions, 21,000+ tag-file mappings), this will worsen proportionally.

## Root Cause

The `tagFileMappings` object from the `graph-data` API groups file mappings by tag_id. A single file can appear in multiple tags' mappings. The frontend iterates over all mappings and counts `has_description: true` entries, which counts the same file multiple times if it has multiple tags.

**Example:** File `2180` has 31 tags and 2 descriptions. It appears 31 times in `tagFileMappings`. The frontend counts 31 "files with descriptions" instead of 1.

## Database Verification

| Metric | Query Result |
|--------|-------------|
| Distinct files with descriptions (`COUNT(DISTINCT file_id) FROM bre_descriptions JOIN mapping`) | **2** |
| Total description mapping rows (`COUNT(*) FROM bre_descriptions JOIN mapping`) | **63** |
| Total tag-file mappings (`COUNT(*) FROM oc_systemtag_object_mapping`) | **21,566** |

---

## Phase 1: Add globalStats to graph-data.get.ts

**File:** `shop_management_app/src/server/api/settings/rag-index/graph-data.get.ts`

### Changes

1. Add new interface for global stats:
```typescript
interface GlobalStats {
  totalFilesWithTags: number
  totalFilesWithDescriptions: number
  totalDescriptionMappings: number
}
```

2. Add three new SQL queries after the existing queries:

```sql
-- Total files with tags (distinct file IDs in mapping table)
SELECT COUNT(DISTINCT objectid::text)::int AS count
FROM oc_systemtag_object_mapping

-- Total distinct files that have at least one description
SELECT COUNT(DISTINCT d.file_id)::int AS count
FROM bre_descriptions d
INNER JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text

-- Total description mapping rows (each description-row that maps to a tagged file)
SELECT COUNT(DISTINCT d.id)::int AS count
FROM bre_descriptions d
INNER JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text
```

3. Add `globalStats` to the return object:
```typescript
return {
  tags,
  edges,
  tagFileMappings,
  globalStats,
}
```

### Why These Queries?

- `totalFilesWithTags`: Counts distinct file IDs in the mapping table. This is what the frontend's `totalFilesWithTags` computed property should return.
- `totalFilesWithDescriptions`: Counts distinct file IDs from `bre_descriptions` that are also in the mapping table. This is the **correct** value for the "Files with Descriptions" stat card.
- `totalDescriptionMappings`: Counts distinct description IDs from `bre_descriptions` that are also in the mapping table. This represents the total number of description entries associated with tagged files.

---

## Phase 2: Fix Frontend sync.vue

**File:** `shop_management_app/src/pages/tags-and-tagging/sync.vue`

### Changes

1. **Update types** (lines 31-62): Add `globalStats` to the graph data interface:
```typescript
interface GlobalStats {
  totalFilesWithTags: number
  totalFilesWithDescriptions: number
  totalDescriptionMappings: number
}

interface GraphData {
  tags: GraphTag[]
  edges: GraphEdge[]
  tagFileMappings: Record<number, TagFileMapping[]>
  globalStats: GlobalStats
}
```

2. **Update state** (line 69): Initialize with globalStats:
```typescript
const graphData = ref<{
  tags: GraphTag[]
  edges: GraphEdge[]
  tagFileMappings: Record<number, TagFileMapping[]>
  globalStats: GlobalStats
}>({
  tags: [],
  edges: [],
  tagFileMappings: {},
  globalStats: {
    totalFilesWithTags: 0,
    totalFilesWithDescriptions: 0,
    totalDescriptionMappings: 0,
  },
})
```

3. **Update fetchGraphData** (lines 145-174): Extract globalStats from response:
```typescript
graphData.value = {
  tags: result.tags || [],
  edges: result.edges || [],
  tagFileMappings: result.tagFileMappings || {},
  globalStats: result.globalStats || {
    totalFilesWithTags: 0,
    totalFilesWithDescriptions: 0,
    totalDescriptionMappings: 0,
  },
}
```

4. **Replace computed properties** (lines 114-142): Use globalStats with defensive Set fallback:

```typescript
// Stats - prefer server-computed globalStats, fall back to defensive Set calculation
const totalTags = computed(() => graphData.value.tags.length)

const totalFilesWithTags = computed(() => {
  // Primary: use server-computed value
  if (graphData.value.globalStats?.totalFilesWithTags > 0) {
    return graphData.value.globalStats.totalFilesWithTags
  }
  // Fallback: defensive Set calculation
  const fileIds = new Set<string>()
  for (const tagId in graphData.value.tagFileMappings) {
    for (const mapping of graphData.value.tagFileMappings[tagId]) {
      fileIds.add(mapping.file_id)
    }
  }
  return fileIds.size
})

const totalFilesWithDescriptions = computed(() => {
  // Primary: use server-computed value
  if (graphData.value.globalStats?.totalFilesWithDescriptions > 0) {
    return graphData.value.globalStats.totalFilesWithDescriptions
  }
  // Fallback: defensive Set calculation (distinct files)
  const fileIds = new Set<string>()
  for (const tagId in graphData.value.tagFileMappings) {
    for (const mapping of graphData.value.tagFileMappings[tagId]) {
      if (mapping.has_description) fileIds.add(mapping.file_id)
    }
  }
  return fileIds.size
})

const totalDescriptions = computed(() => {
  // Primary: use server-computed value
  if (graphData.value.globalStats?.totalDescriptionMappings > 0) {
    return graphData.value.globalStats.totalDescriptionMappings
  }
  // Fallback: defensive Set calculation (count description rows, not distinct files)
  let count = 0
  for (const tagId in graphData.value.tagFileMappings) {
    for (const mapping of graphData.value.tagFileMappings[tagId]) {
      if (mapping.has_description) count++
    }
  }
  return count
})
```

---

## Phase 3: Add Paginated Tag-Files Endpoint

**New File:** `shop_management_app/src/server/api/settings/rag-index/tag-files.get.ts`

### Purpose

Replace the need to transfer all `tagFileMappings` in the `graph-data` response. At scale, this payload can be 1.5MB+. With pagination, we only fetch the files for the specific tag the user is viewing.

### Implementation

```typescript
/**
 * Tag Files API
 * Returns paginated list of files associated with a specific tag.
 */

import { Pool } from 'pg'

interface TagFileResult {
  file_id: string
  file_name: string
  has_description: boolean
}

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const tagId = query.tag_id as string
  const limit = Math.min(parseInt(query.limit as string) || 50, 200)
  const offset = parseInt(query.offset as string) || 0

  if (!tagId) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Missing required parameter: tag_id',
    })
  }

  const dbHost = process.env.DB_HOST || 'localhost'
  const dbPort = Number(process.env.DB_PORT) || 5432
  const dbName = process.env.DB_NAME || 'nextpsql'
  const dbUser = process.env.DB_USER || 'nextuser'
  const dbPassword = process.env.DB_PASSWORD || ''

  const pool = new Pool({
    host: dbHost,
    port: dbPort,
    database: dbName,
    user: dbUser,
    password: dbPassword,
  })

  try {
    // Get total count
    const countQuery = `
      SELECT COUNT(DISTINCT m.objectid::text)::int AS count
      FROM oc_systemtag_object_mapping m
      WHERE m.systemtagid = $1
    `
    const countResult = await pool.query(countQuery, [tagId])
    const total = parseInt(countResult.rows[0].count)

    // Get paginated files with description status
    const filesQuery = `
      SELECT 
        m.objectid::text AS file_id,
        fc.name AS file_name,
        CASE WHEN d.file_id IS NOT NULL THEN true ELSE false END AS has_description
      FROM oc_systemtag_object_mapping m
      LEFT JOIN oc_filecache fc ON m.objectid::text = fc.fileid::text
        AND fc.name NOT LIKE '.%' AND fc.mimetype IN (
          SELECT id FROM oc_mimetypes WHERE mimetype LIKE 'image/%'
        )
      LEFT JOIN bre_descriptions d ON m.objectid::text = d.file_id
      WHERE m.systemtagid = $1
      ORDER BY fc.name
      LIMIT $2 OFFSET $3
    `
    const filesResult = await pool.query(filesQuery, [tagId, limit, offset])
    
    const files: TagFileResult[] = filesResult.rows.map(row => ({
      file_id: row.file_id,
      file_name: row.file_name || 'Unknown',
      has_description: row.has_description,
    }))

    return {
      files,
      total,
      limit,
      offset,
    }
  } catch (error: any) {
    console.error('[tag-files] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch tag files: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
```

---

## Phase 4: Update sync.vue to Use Paginated Endpoint

### Changes

1. **Update state** (around line 91): Add pagination state for tag files:
```typescript
const tagFiles = ref<Map<number, TagFileResult[]>>(new Map())
const tagFilesTotal = ref<Map<number, number>>(new Map())
const tagFilesLoading = ref<Map<number, boolean>>(new Map())
```

2. **Add fetch function:**
```typescript
async function fetchTagFiles(tagId: number, forceRefresh = false) {
  const loadingKey = String(tagId)
  if (tagFilesLoading.value.get(tagId) && !forceRefresh) return
  
  tagFilesLoading.value.set(tagId, true)
  try {
    const result = await $fetch('/api/settings/rag-index/tag-files', {
      method: 'GET',
      query: { tag_id: String(tagId), limit: '200', offset: '0' },
    })
    tagFiles.value.set(tagId, result.files || [])
    tagFilesTotal.value.set(tagId, result.total || 0)
  } catch (error: any) {
    console.error(`Failed to fetch tag files for tag ${tagId}:`, error)
  } finally {
    tagFilesLoading.value.set(tagId, false)
  }
}
```

3. **Update onTagClick** (line 353): Call `fetchTagFiles` instead of using in-memory data:
```typescript
async function onTagClick(tag: GraphTag) {
  selectedTag.value = tag
  selectedFileDetail.value = null
  await fetchTagFiles(tag.id)
}
```

4. **Update template references**: Replace `graphData.tagFileMappings[selectedTag.id]` with `tagFiles.value.get(selectedTag.id) || []`

5. **Update List View** (line 444): Use paginated endpoint instead of graph data:
```typescript
async function fetchListTagFiles(tagId: number) {
  if (expandedListTag.value === tagId) {
    expandedListTag.value = null
    listTagFiles.value = []
    return
  }
  
  listTagFilesLoading.value = true
  expandedListTag.value = tagId
  
  try {
    const result = await $fetch('/api/settings/rag-index/tag-files', {
      method: 'GET',
      query: { tag_id: String(tagId), limit: '500', offset: '0' },
    })
    listTagFiles.value = result.files || []
  } catch (error: any) {
    console.error('Failed to fetch tag files:', error)
  } finally {
    listTagFilesLoading.value = false
  }
}
```

6. **Update Descriptions View** (line 480): Use new dedicated endpoint for descriptions:
```typescript
// Replace the O(n) loop with a dedicated API call
async function fetchDescriptions() {
  descriptionsLoading.value = true
  try {
    const result = await $fetch('/api/settings/rag-index/descriptions-list', {
      method: 'GET',
      query: {
        limit: String(descriptionsPageSize),
        offset: String(descriptionsPage.value * descriptionsPageSize),
        ...(descriptionsSearchQuery.value && { search: descriptionsSearchQuery.value }),
        ...(descriptionsFilter.value !== 'all' && { filter: descriptionsFilter.value }),
      },
    })
    descriptions.value = result.descriptions || []
    descriptionsTotal.value = result.total || 0
  } catch (error: any) {
    console.error('Failed to fetch descriptions:', error)
  } finally {
    descriptionsLoading.value = false
  }
}
```

7. **Remove `tagFileMappings` from graph-data response** (optional, Phase 5): Once Phase 4 is verified, the `tagFileMappings` object can be removed from the `graph-data` API response entirely, saving significant bandwidth.

---

## Additional: Descriptions List Endpoint

**New File:** `shop_management_app/src/server/api/settings/rag-index/descriptions-list.get.ts`

```typescript
/**
 * Descriptions List API
 * Returns paginated list of all descriptions with file info.
 */

import { Pool } from 'pg'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const search = (query.search as string) || ''
  const filter = (query.filter as string) || 'all'
  const limit = Math.min(parseInt(query.limit as string) || 50, 200)
  const offset = parseInt(query.offset as string) || 0

  const dbHost = process.env.DB_HOST || 'localhost'
  // ... pool setup ...

  try {
    // Build WHERE clause
    const whereConditions: string[] = []
    const params: any[] = []
    let paramIndex = 1

    if (search) {
      whereConditions.push('(fc.name ILIKE $${paramIndex} OR d.description ILIKE $${paramIndex})')
      params.push(`%${search}%`)
      paramIndex++
    }

    const whereClause = whereConditions.length > 0 ? `WHERE ${whereConditions.join(' AND ')}` : ''

    // Get total count
    const countQuery = `
      SELECT COUNT(DISTINCT d.id)::int AS count
      FROM bre_descriptions d
      JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text
      JOIN oc_filecache fc ON d.file_id = fc.fileid::text
      ${whereClause}
    `
    const countResult = await pool.query(countQuery, params)
    const total = parseInt(countResult.rows[0].count)

    // Get paginated descriptions
    const descQuery = `
      SELECT 
        d.id,
        d.file_id,
        fc.name AS file_name,
        d.description,
        d.pinned,
        TO_CHAR(d.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS createdAt
      FROM bre_descriptions d
      JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text
      JOIN oc_filecache fc ON d.file_id = fc.fileid::text
      ${whereClause}
      ORDER BY d.created_at DESC
      LIMIT $${paramIndex} OFFSET $${paramIndex + 1}
    `
    const descResult = await pool.query(descQuery, [...params, limit, offset])
    
    return {
      descriptions: descResult.rows.map(row => ({
        id: parseInt(row.id),
        file_id: row.file_id,
        file_name: row.file_name || 'Unknown',
        description: row.description,
        pinned: row.pinned,
        createdAt: row.createdAt,
      })),
      total,
      limit,
      offset,
    }
  } catch (error: any) {
    // ... error handling ...
  }
})
```

---

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `graph-data.get.ts` | Modified | Add `globalStats` object with server-computed counts |
| `sync.vue` | Modified | Use `globalStats` with defensive Set fallback |
| `tag-files.get.ts` | **New** | Paginated endpoint for tag-file mappings |
| `descriptions-list.get.ts` | **New** | Paginated endpoint for descriptions list |
| `graph-data.get.ts` (Phase 5) | Modified | Remove `tagFileMappings` from response |

## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| "Files with Descriptions" stat | Wrong (63) | Correct (2) |
| "Total Descriptions" stat | Wrong (63) | Correct (63 mapping rows) |
| `graph-data` payload (current) | ~1.5MB | ~1.5MB (unchanged, Phase 5 reduces to ~50KB) |
| `graph-data` payload (scale) | ~15MB | ~50KB (after Phase 5) |
| Tag detail panel load | In-memory (instant) | 1 API call (~50ms) |
| Server CPU for stats | N/A | <1ms per query |
