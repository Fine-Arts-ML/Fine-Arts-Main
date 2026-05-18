/**
 * Composable for managing the Tags & Tagging pipeline state across pages.
 * Uses Nuxt useState for cross-page reactive state sharing.
 */

export interface TagInfo {
  id: number
  name: string
  num_files: number
}

export interface CleanedTag {
  original: string
  cleaned: string[]
}

export interface FileInfo {
  file_id: string
  file_name: string
  file_path: string
  file_size: number
  mime_type: string
  last_modified: string | null
  is_directory: boolean
  existing_tags: Array<{ id: number; name: string }>
  is_tagged: boolean
  tag_count: number
  preview_url?: string
}

export function useTagPipeline() {
  // Shared state across pipeline pages
  const selectedFileIds = useState<number[]>('tagPipeline.selectedFileIds', () => [])
  const selectedFiles = useState<FileInfo[]>('tagPipeline.selectedFiles', () => [])
  const generatedTags = useState<Map<number, TagInfo[]> | null>('tagPipeline.generatedTags', () => null)
  const generatedDescriptions = useState<Map<number, string> | null>('tagPipeline.generatedDescriptions', () => null)
  const pendingTags = useState<Map<number, string[]> | null>('tagPipeline.pendingTags', () => null)
  const currentStep = useState<string>('tagPipeline.currentStep', () => 'scan-files')
  
  // Pipeline steps definition
  const steps = [
    { id: 'scan-files', label: 'Scan Files', icon: '🔍' },
    { id: 'tags', label: 'Tags & Descriptions', icon: '🏷️' },
    { id: 'review-data', label: 'Review Data', icon: '✅' },
    { id: 'sync', label: 'Sync', icon: '🔄' },
  ]
  
  /**
   * Set the current pipeline step
   */
  function setStep(stepId: string) {
    currentStep.value = stepId
  }
  
  /**
   * Check if a pipeline step is complete
   */
  function isStepComplete(stepId: string): boolean {
    switch (stepId) {
      case 'scan-files':
        return (selectedFileIds.value?.length ?? 0) > 0
      case 'tags':
        return (generatedTags.value?.size ?? 0) > 0
      case 'review-data':
        return (pendingTags.value?.size ?? 0) > 0
      case 'sync':
        return false // Sync is the final step
      default:
        return false
    }
  }
  
  /**
   * Reset all pipeline state
   */
  function resetPipeline() {
    selectedFileIds.value = []
    selectedFiles.value = []
    generatedTags.value = new Map()
    generatedDescriptions.value = new Map()
    pendingTags.value = new Map()
    currentStep.value = 'scan-files'
  }
  
  /**
   * Add file IDs to selection
   */
  function addFileIds(fileIds: number[]) {
    if (!selectedFileIds.value) {
      selectedFileIds.value = fileIds
    } else {
      const existing = new Set(selectedFileIds.value)
      for (const id of fileIds) {
        existing.add(id)
      }
      selectedFileIds.value = Array.from(existing)
    }
  }
  
  /**
   * Remove a single file from selection by its file_id (string)
   */
  function removeFileId(fileId: string) {
    const numId = Number(fileId)
    selectedFileIds.value = (selectedFileIds.value as number[] | undefined)?.filter((id: number) => id !== numId) ?? []
    selectedFiles.value = (selectedFiles.value as FileInfo[] | undefined)?.filter((f: FileInfo) => f.file_id !== fileId) ?? []
  }

  /**
   * Clear file selection
   */
  function clearSelection() {
    selectedFileIds.value = []
    selectedFiles.value = []
  }
  
  /**
   * Set selected file details (transferred from scan-files page)
   */
  function setSelectedFiles(files: FileInfo[]) {
    selectedFiles.value = files
    const ids = files.map(f => Number(f.file_id))
    addFileIds(ids)
  }
  
  /**
   * Set generated tags for files
   */
  function setGeneratedTags(fileId: number, tags: TagInfo[]) {
    if (!generatedTags.value) {
      generatedTags.value = new Map()
    }
    generatedTags.value.set(fileId, tags)
  }
  
  /**
   * Set generated description for a file
   */
  function setGeneratedDescription(fileId: number, description: string) {
    if (!generatedDescriptions.value) {
      generatedDescriptions.value = new Map()
    }
    generatedDescriptions.value.set(fileId, description)
  }
  
  /**
   * Set pending tags for application
   */
  function setPendingTags(fileId: number, tags: string[]) {
    if (!pendingTags.value) {
      pendingTags.value = new Map()
    }
    pendingTags.value.set(fileId, tags)
  }
  
  /**
   * Get generated tags for a specific file
   */
  function getGeneratedTags(fileId: number): TagInfo[] | undefined {
    return generatedTags.value?.get(fileId)
  }
  
  /**
   * Get generated description for a specific file
   */
  function getGeneratedDescription(fileId: number): string | undefined {
    return generatedDescriptions.value?.get(fileId)
  }
  
  /**
   * Check if tags have been generated for any file
   */
  function hasGeneratedTags(): boolean {
    return (generatedTags.value?.size ?? 0) > 0
  }
  
  /**
   * Check if there are pending tags to apply
   */
  function hasPendingTags(): boolean {
    return (pendingTags.value?.size ?? 0) > 0
  }
  
  return {
    // State
    selectedFileIds,
    selectedFiles,
    generatedTags,
    generatedDescriptions,
    pendingTags,
    currentStep,
    steps,
    
    // Methods
    setStep,
    isStepComplete,
    resetPipeline,
    addFileIds,
    removeFileId,
    clearSelection,
    setSelectedFiles,
    setGeneratedTags,
    setGeneratedDescription,
    setPendingTags,
    getGeneratedTags,
    getGeneratedDescription,
    hasGeneratedTags,
    hasPendingTags,
  }
}
