<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useAuth } from '~/composables/useAuth'
import { useTagPipeline } from '~/composables/useTagPipeline'
import FileBrowserTree from '~/components/FileBrowserTree.vue'
import type { FileFilter as TreeFileFilter } from '~/components/FileBrowserTree.vue'
import {
  FileText, Image as ImageIcon,
  CheckSquare, Square, CheckCircle, Filter,
} from 'lucide-vue-next'

const { isAdmin, isAuthenticated } = useAuth()
const {
  selectedFileIds,
  setSelectedFiles,
} = useTagPipeline()

definePageMeta({
  middleware: 'tags-pipeline',
})

useHead({
  title: 'Select Files - Tags & Descriptions',
})

// Types
interface FileInfo {
  file_id: string
  file_name: string
  file_path: string
  file_size: number
  mime_type: string
  last_modified: string | null
  is_directory: boolean
  existing_tags: Array<{ id: number; name: string; color: string }>
  is_tagged: boolean
  tag_count: number
  preview_url?: string
}

// State
const scanResults = ref<FileInfo[]>([])
const isScanning = ref(false)

// Unified selected file paths (works for both folder and individual file selections)
const selectedFilePaths = ref<Set<string>>(new Set())

function handleSelectedFilesUpdate(files: Set<string>) {
  selectedFilePaths.value = files
  console.log('[scan-files] Selected file paths updated:', Array.from(files))
}

// Helper: Get unique parent folder paths from an array of file paths
function getParentFolderPaths(filePaths: Set<string>): { folderPaths: string[]; userId: string } {
  const folderSet = new Set<string>()
  let userId = 'Tom'
  
  for (const filePath of filePaths) {
    // Extract userId from path format: "/Tom/Malerei/..."
    const pathParts = filePath.split('/')
    if (pathParts.length >= 2 && pathParts[1]) {
      userId = pathParts[1]
    }
    // Get parent folder (remove filename)
    const parentFolder = filePath.substring(0, filePath.lastIndexOf('/'))
    if (parentFolder) {
      folderSet.add(parentFolder)
    }
  }
  
  return { folderPaths: Array.from(folderSet), userId }
}

// Helper: Filter scan results to only include selected file paths
function filterToSelectedFiles(scanResults: FileInfo[], selectedPaths: Set<string>): FileInfo[] {
  if (selectedPaths.size === 0) return scanResults
  
  return scanResults.filter(file => selectedPaths.has(file.file_path))
}

// Helper: Perform the actual scan and return results
async function performScan(folderPaths: string[], userId: string): Promise<FileInfo[]> {
  const allFiles: FileInfo[] = []
  
  for (const folderPath of folderPaths) {
    const result = await $fetch('/api/settings/rag-index/scan-directory', {
      method: 'GET',
      params: { path: folderPath, userId, storageId: '1' },
    })
    
    const scanData = result?.data || result
    const files = scanData?.files || []
    files.forEach((file: FileInfo) => allFiles.push(file))
  }
  
  return allFiles
}

async function handleProceed() {
  // Always scan based on current selectedFilePaths to support re-selection
  console.log('[scan-files] Proceed: selectedFilePaths:', Array.from(selectedFilePaths.value))
  
  if (selectedFilePaths.value.size === 0) {
    alert('Please select files or folders first.')
    return
  }
  
  isScanning.value = true
  try {
    const { folderPaths, userId } = getParentFolderPaths(selectedFilePaths.value)
    console.log('[scan-files] Proceed: Scanning parent folders for selected files:', folderPaths)
    
    const allFiles = await performScan(folderPaths, userId)
    const filteredFiles = filterToSelectedFiles(allFiles, selectedFilePaths.value)
    
    console.log('[scan-files] Proceed: Scanned and filtered', filteredFiles.length, 'files')
    scanResults.value = filteredFiles
    setSelectedFiles(filteredFiles)
    
    if (filteredFiles.length === 0) {
      alert('No files found in the selected paths. Please select files or folders.')
      return
    }
  } catch (error: any) {
    console.error('[scan-files] Proceed: Scan failed:', error)
    alert(`Failed to scan folders: ${error.message || 'Unknown error'}`)
    return
  } finally {
    isScanning.value = false
  }
  
  // Navigate to the tags page
  console.log('[scan-files] Proceed: Navigating to tags page with', selectedFileIds.value.length, 'files')
  navigateTo('/tags-and-tagging/tags')
}
</script>

<template>
  <div class="space-y-6 flex flex-col h-full">
    <!-- File Browser Tree -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col flex-1 min-h-0">
      <div class="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0">
        <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <FileText class="w-4 h-4" />
          Select Folders to Scan
        </h3>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          Choose folders and files from the tree below. Only folders configured by your administrator are available.
        </p>
      </div>

      <div class="p-4 flex-1 min-h-0">
        <FileBrowserTree
          :accessible-folders="[]"
          @update:selected-files="handleSelectedFilesUpdate"
          @proceed="handleProceed"
        />
      </div>
    </div>

  </div>
</template>
