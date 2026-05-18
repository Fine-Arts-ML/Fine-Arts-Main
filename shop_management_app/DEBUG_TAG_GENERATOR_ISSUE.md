# Debug: Tag Generator Shows "No Files Selected" for New Files

## Issue Description

When selecting new files to tag/describe that haven't been tagged before:
1. User selects files in the Scan Files tree view
2. The "Tag & Describe N Files" button shows the correct count
3. User clicks the button and navigates to the Tags & Descriptions Generator
4. The Generator page shows "No Files Selected" - empty state

However, the workflow WORKS for already-tagged files (files that were previously scanned).

---

## Root Cause

The bug was in the `handleProceed()` function in [`scan-files.vue`](shop_management_app/src/pages/tags-and-tagging/scan-files.vue).

When the user selected **individual files** (not folders) in the tree view:
1. The FileBrowserTree component tracked file selections and emitted their paths via `emit('update:selectedFolders', selectedPaths)`
2. These paths were stored in `selectedFolderPaths` in `scan-files.vue`
3. When "Tag & Describe N Files" was clicked, `handleProceed()` iterated over `selectedFolderPaths` and called the `scan-directory` API for each path
4. **The `scan-directory` API expects a FOLDER path, not a FILE path.** When file paths were passed, the API returned an empty file list
5. `setSelectedFiles(allFiles)` was called with an empty array
6. When `tags.vue` loaded, `selectedFiles.value` was empty, showing "No Files Selected"

---

## Fix Applied

### Solution: Unified File Path Tracking

Instead of differentiating between folder and file selections after the user makes them, we now collect ALL selected file paths into a single unified state, regardless of whether the user selected folders, files, or both.

### Changes Made

#### 1. [`FileBrowserTree.vue`](shop_management_app/src/components/FileBrowserTree.vue)

**Added new emit:**
```typescript
const emit = defineEmits<{
  'update:selectedFolders': [folders: Set<string>]
  'update:selectedFiles': [files: Set<string>]  // NEW
  'scan': [paths: string[]]
  'filter-change': [filter: FileFilter]
  'proceed': []
}>()
```

**Added `getSelectedFilePaths()` function:**
```typescript
function getSelectedFilePaths(): Set<string> {
  const paths = new Set<string>()
  
  function collectFilePaths(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected && item.type === 'file') {
        paths.add(item.path)
      }
      if (item.children && item.type === 'directory') {
        collectFilePaths(item.children)
      }
    }
  }
  
  collectFilePaths(rootFolders.value)
  return paths
}
```

**Emitted file paths alongside folder paths in all selection handlers:**
- `toggleItemSelection()`
- `applyPersistedSelection()`
- `selectAll()`

#### 2. [`scan-files.vue`](shop_management_app/src/pages/tags-and-tagging/scan-files.vue)

**Removed deprecated code:**
- Removed `handleScan()` function (no longer needed - the workflow uses selection + proceed, not a separate scan action)
- Removed `selectedFolderPaths` state (replaced by unified `selectedFilePaths`)
- Removed `@scan="handleScan"` and `@update:selected-folders="handleSelectedFoldersUpdate"` from template

**Added new state and handlers:**
```typescript
// Unified selected file paths (works for both folder and individual file selections)
const selectedFilePaths = ref<Set<string>>(new Set())

function handleSelectedFilesUpdate(files: Set<string>) {
  selectedFilePaths.value = files
}
```

**Added helper functions:**
```typescript
// Get unique parent folder paths from file paths
function getParentFolderPaths(filePaths: Set<string>): { folderPaths: string[]; userId: string }

// Filter scan results to only include selected file paths
function filterToSelectedFiles(scanResults: FileInfo[], selectedPaths: Set<string>): FileInfo[]

// Perform the actual scan
async function performScan(folderPaths: string[], userId: string): Promise<FileInfo[]>
```

**Updated `handleProceed()` logic:**
```typescript
async function handleProceed() {
  if (selectedFileIds.value.length === 0) {
    isScanning.value = true
    try {
      let allFiles: FileInfo[] = []
      
      // Scan parent folders of selected files, then filter results
      if (selectedFilePaths.value.size > 0) {
        const { folderPaths, userId } = getParentFolderPaths(selectedFilePaths.value)
        allFiles = await performScan(folderPaths, userId)
        allFiles = filterToSelectedFiles(allFiles, selectedFilePaths.value)
      }
      
      setSelectedFiles(allFiles)
    } catch (error: any) {
      // ... error handling
    }
  }
  
  navigateTo('/tags-and-tagging/tags')
}
```

---

## How It Works Now

1. User selects files/folders in the tree view
2. FileBrowserTree emits `@update:selected-files` with ALL selected file paths (extracted from both folder and file selections)
3. `handleProceed()` receives these paths
4. If no files have been scanned:
   - Extract parent folder paths from the selected file paths
   - Scan those parent folders using the `scan-directory` API
   - Filter the scan results to only include the originally selected files
5. Navigate to tags page with the filtered results

---

## Files Modified

| File | Changes |
|------|---------|
| [`FileBrowserTree.vue`](shop_management_app/src/components/FileBrowserTree.vue) | Added `update:selectedFiles` emit, `getSelectedFilePaths()` function |
| [`scan-files.vue`](shop_management_app/src/pages/tags-and-tagging/scan-files.vue) | Removed deprecated `handleScan()`, unified file path tracking, updated `handleProceed()` |

---

## Status: FIXED
