import { ref, watch } from 'vue'

const STORAGE_KEY = 'gallery-column-count'
const DEFAULT_COLUMNS = 3
const MIN_COLUMNS = 1
const MAX_COLUMNS = 6

export function useGalleryLayout(initialColumns?: number) {
  // Read from localStorage on first load, fallback to initial or default
  const saved = typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
  const columns = ref(initialColumns ?? (saved ? parseInt(saved, 10) : DEFAULT_COLUMNS))

  // Ensure columns is within valid range
  const validColumns = ref(Math.max(MIN_COLUMNS, Math.min(MAX_COLUMNS, columns.value)))

  // Watch for changes and persist
  watch(validColumns, (newVal) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, String(newVal))
    }
  })

  function setColumns(n: number) {
    validColumns.value = Math.max(MIN_COLUMNS, Math.min(MAX_COLUMNS, n))
  }

  return {
    columns: validColumns,
    setColumns
  }
}
