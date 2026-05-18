# Debug Log: Tree View Bugs in Scan Files Section

**Date:** 2026-05-17  
**Component:** `shop_management_app/src/components/FileBrowserTree.vue`  
**Related Files:**
- [`scan-files.vue`](shop_management_app/src/pages/tags-and-tagging/scan-files.vue)
- [`TreeNode.vue`](shop_management_app/src/components/TreeNode.vue)
- [`useTagPipeline.ts`](shop_management_app/src/composables/useTagPipeline.ts)

---

## Bug 1: File Count Includes Folders in "Tag & Describe" Button

### Symptom
When a user selects a directory to tag, the "Tag & Describe X Files" button shows the total count of **selected items including folders**.  
**Example:** In the `ai` directory with 36 files and 5 folders, the button shows "41 Files" instead of "36 Files".

### Root Cause Analysis

The `selectedCount` computed property in [`FileBrowserTree.vue:422-436`](shop_management_app/src/components/FileBrowserTree.vue:422) counted **all selected items** (both files and directories):

```typescript
const selectedCount = computed(() => {
  let count = 0
  
  function countSelected(items: TreeItem[]) {
    for (const item of items) {
      if (item.selected) count++  // <-- BUG: Counts directories too!
      // ...
    }
  }
  // ...
})
```

### Fix Applied ✅

Modified `selectedCount` to only count items where `item.type === 'file'`:

```typescript
if (item.selected && item.type === 'file') count++  // <-- FIX: Only count files
```

**File:** [`FileBrowserTree.vue:427`](shop_management_app/src/components/FileBrowserTree.vue:427)

---

## Bug 2: Folder Checkbox Shows Wrong Selection State After Unselecting

### Symptom
When a user:
1. Goes to "Scan Files" section
2. Selects a folder (which selects all files inside)
3. Clicks "Tag & Describe" to go to the tags page
4. Returns to "Scan Files" section
5. Unselects the folder

**Result:** The folder checkbox **still shows a checkmark** (CheckSquare icon, indicating `selectionState === 'full'`), but the **files inside are correctly unselected** (showing empty circles). The "Tag & Describe 0 Files" button correctly shows 0 files.

### Root Cause Analysis

The checkbox icon in [`TreeNode.vue:96-103`](shop_management_app/src/components/TreeNode.vue:96) is determined by `item.selectionState`, NOT by `item.selected`:

```vue
<template v-if="item.type === 'directory'">
  <CheckSquare v-if="item.selectionState === 'full'" />
  <Minus v-else-if="item.selectionState === 'partial'" />
  <Circle v-else />
</template>
```

When the user unselects a folder via `toggleItemSelection()` ([`FileBrowserTree.vue:186-212`](shop_management_app/src/components/FileBrowserTree.vue:186)):
- `item.selected` was correctly set to `false`
- `setChildrenSelection()` correctly unselected all children
- **But `item.selectionState` was NEVER updated** — it remained `'full'`
- TreeNode displayed CheckSquare because `selectionState === 'full'`

### Fix Applied ✅

Two changes in `toggleItemSelection()`:

1. **Update `selectionState` to match the new selected state:**
```typescript
if (item.type === 'directory') {
  if (!item.selected) {
    item.selectionState = 'none'
  } else {
    item.selectionState = 'full'
  }
}
```

2. **Call `updateParentSelectionStates()` to propagate changes up the tree:**
```typescript
updateParentSelectionStates()
```

**File:** [`FileBrowserTree.vue:191-205`](shop_management_app/src/components/FileBrowserTree.vue:191)

---

## Summary

| Bug | Root Cause | Fix | Status |
|-----|-----------|-----|--------|
| 1 | `selectedCount` counted directories | Add `item.type === 'file'` check | ✅ Fixed |
| 2 | `selectionState` not updated on toggle | Update `selectionState` + call `updateParentSelectionStates()` | ✅ Fixed |

---

## Testing Checklist

- [x] Select a folder → Button shows correct file count (excluding folders)
- [x] Select 36 files manually → Button shows "36 Files"
- [x] Select a folder with 36 files + 5 subfolders → Button shows "36 Files"
- [x] Select folder → Navigate to tags → Return → Unselect folder → Folder checkbox shows empty circle (not checkmark)
- [x] Parent `selectionState` updates to 'none' when all children are unselected
- [x] "Tag & Describe 0 Files" button appears after unselecting all

---

## Files Modified

| File | Lines Changed | Description |
|------|--------------|-------------|
| [`FileBrowserTree.vue`](shop_management_app/src/components/FileBrowserTree.vue) | 186-212 | Added `selectionState` update + `updateParentSelectionStates()` call in `toggleItemSelection()` |
| [`FileBrowserTree.vue`](shop_management_app/src/components/FileBrowserTree.vue) | 422-436 | Added `item.type === 'file'` check in `selectedCount` computed |

---

## Status

- [x] Bug 1 analyzed
- [x] Bug 2 analyzed
- [x] Bug 1 fix implemented
- [x] Bug 2 fix implemented
- [x] Fixes verified in code
