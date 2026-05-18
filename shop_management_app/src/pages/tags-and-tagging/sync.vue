<script setup lang="ts">
import { useAuth } from '~/composables/useAuth'
import { 
  Tag, 
  RefreshCw,
  Search,
  Filter,
  X,
  Image as ImageIcon,
  FileText,
  ChevronDown,
  ChevronUp,
  Trash2,
  Eye,
  EyeOff,
  ZoomIn
} from 'lucide-vue-next'

const { isAdmin, isAuthenticated } = useAuth()

definePageMeta({
  layout: 'default',
  middleware: 'admin',
})

useHead({
  title: 'Tag Management - Art Management',
})

// ========== Types ==========
interface GraphTag {
  id: number
  name: string
  num_files: number
  files_with_descriptions: number
}

interface GraphEdge {
  tag_id_1: number
  tag_id_2: number
  shared_files: number
}

interface TagFileMapping {
  file_id: string
  file_name: string
  has_description: boolean
}

interface GlobalStats {
  totalFilesWithTags: number
  totalFilesWithDescriptions: number
  totalDescriptionMappings: number
}

interface FileDetail {
  file_id: string
  file_name: string
  preview_url: string
  descriptions: Array<{ id: number; description: string; pinned: boolean; createdAt: string }>
}

interface ListTag {
  id: number
  name: string
  num_files: number
  files_with_descriptions: number
}

// ========== State ==========
const isLoading = ref(false)
const activeTab = ref<'graph' | 'list' | 'descriptions'>('graph')

// Graph state
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

// Tag files cache (for paginated endpoint)
const tagFilesCache = ref<Map<number, TagFileMapping[]>>(new Map())
const tagFilesCacheLoading = ref<Map<number, boolean>>(new Map())
const selectedTag = ref<GraphTag | null>(null)
const selectedFileDetail = ref<FileDetail | null>(null)
const graphInstance = ref<any>(null)
const graphContainer = ref<HTMLDivElement | null>(null)
const networkDataSet = ref<{ nodes: any; edges: any } | null>(null)

// List view state
const listTags = ref<ListTag[]>([])
const listLoading = ref(false)
const listSearchQuery = ref('')
const listFilterDesc = ref<'all' | 'has' | 'none'>('all')
const listFilterColor = ref<'all' | 'true' | 'false'>('all')
const listSortBy = ref<'name' | 'num_files'>('name')
const listSortDirection = ref<'asc' | 'desc'>('asc')
const listPage = ref(0)
const listTotal = ref(0)
const listPageSize = 50
const expandedListTag = ref<number | null>(null)
const listTagFiles = ref<Array<{ file_id: string; file_name: string; has_description: boolean }>>([])
const listTagFilesLoading = ref(false)

// Descriptions view state
const descriptionsLoading = ref(false)
const descriptionsSearchQuery = ref('')
const descriptionsFilter = ref<'all' | 'has' | 'none'>('all')
const descriptionsPage = ref(0)
const descriptionsTotal = ref(0)
const descriptionsPageSize = 50
const descriptions = ref<Array<{
  file_id: string
  file_name: string
  preview_url: string
  descriptions: Array<{ id: number; description: string; pinned: boolean; createdAt: string }>
}>>([])
const selectedDescFileDetail = ref<FileDetail | null>(null)

// Stats - prefer server-computed globalStats, fall back to defensive Set calculation
const totalTags = computed(() => graphData.value.tags.length)

const totalFilesWithTags = computed(() => {
  // Primary: use server-computed value
  if (graphData.value.globalStats?.totalFilesWithTags && graphData.value.globalStats.totalFilesWithTags > 0) {
    return graphData.value.globalStats.totalFilesWithTags
  }
  // Fallback: defensive Set calculation (distinct files)
  const fileIds = new Set<string>()
  for (const tagId in graphData.value.tagFileMappings) {
    for (const mapping of graphData.value.tagFileMappings[tagId]) {
      fileIds.add(mapping.file_id)
    }
  }
  return fileIds.size
})

const totalFilesWithDescriptions = computed(() => {
  // Primary: use server-computed value (distinct files with descriptions)
  if (graphData.value.globalStats?.totalFilesWithDescriptions && graphData.value.globalStats.totalFilesWithDescriptions > 0) {
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
  // Primary: use server-computed value (total description mapping rows)
  if (graphData.value.globalStats?.totalDescriptionMappings && graphData.value.globalStats.totalDescriptionMappings > 0) {
    return graphData.value.globalStats.totalDescriptionMappings
  }
  // Fallback: count description rows (not distinct files - each mapping row counts)
  let count = 0
  for (const tagId in graphData.value.tagFileMappings) {
    for (const mapping of graphData.value.tagFileMappings[tagId]) {
      if (mapping.has_description) count++
    }
  }
  return count
})

// ========== Graph Methods ==========
async function fetchGraphData() {
  isLoading.value = true
  try {
    const result = await $fetch('/api/settings/rag-index/graph-data', {
      method: 'GET',
    })
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
    
    // Filter out tags with only 1 file for cleaner graph
    const filteredTags = graphData.value.tags.filter((t: GraphTag) => t.num_files >= 1)
    const tagIds = new Set(filteredTags.map((t: GraphTag) => t.id))
    const filteredEdges = graphData.value.edges.filter((e: GraphEdge) => 
      tagIds.has(e.tag_id_1) && tagIds.has(e.tag_id_2)
    )
    
    graphData.value.tags = filteredTags
    graphData.value.edges = filteredEdges
    
    initNetwork()
  } catch (error: any) {
    console.error('Failed to fetch graph data:', error)
    alert(`Failed to fetch graph data: ${error.message || 'Unknown error'}`)
  } finally {
    isLoading.value = false
  }
}

function initNetwork() {
  // Dynamic import for client-side only
  import('vis-network/standalone/esm/vis-network.mjs').then(({ Network, DataSet }) => {
      // Reset positions for fresh layout
      for (let i = 0; i < graphData.value.tags.length; i++) {
        delete graphData.value.tags[i].x
        delete graphData.value.tags[i].y
      }

      const nodes = new DataSet(
        graphData.value.tags.map((tag: GraphTag) => ({
          id: String(tag.id),
          label: tag.name,
          x: undefined,
          y: undefined,
          shape: 'dot',
          size: Math.max(10, Math.min(30, 10 + tag.num_files * 0.5)),
          title: buildNodeTooltip(tag),
          color: {
            background: '#3498db',
            border: '#2980b9',
          },
          font: { size: 12, face: 'Inter, system-ui, sans-serif' },
        }))
      )
      
      // Filter edges - keep all edges sharing >= 1 file, sort by strength, cap for performance
      // Sort by shared_files descending to keep strongest connections first
      const filteredEdges = graphData.value.edges
        .filter((edge: GraphEdge) => edge.shared_files >= 1)
        .sort((a, b) => b.shared_files - a.shared_files)
        .slice(1, 5000) // Limit to top 1000 strongest connections
      
      const edges = new DataSet(
        filteredEdges.map((edge: GraphEdge) => ({
          id: `${edge.tag_id_1}-${edge.tag_id_2}`,
          from: String(edge.tag_id_1),
          to: String(edge.tag_id_2),
          width: 0.6,
          title: `Shared by ${edge.shared_files} file(s)`,
          color: { inherit: 'from' },
          smooth: { type: 'continuous' },
        }))
      )
      
      networkDataSet.value = { nodes, edges }
      
      const options = {
        nodes: {
          shape: 'dot',
          scaling: {
            min: 10,
            max: 60,
          },
          font: {
            size: 12,
            face: 'Tahoma, Inter, system-ui, sans-serif',
          },
        },
        physics: {
          stabilization: false,
          barnesHut: {
            gravitationalConstant: -8000,
            springConstant: 0.0002,
            springLength: 400,
          },
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          clickToUse: true,
          dragNodes: true,
          dragView: true,
          zoomView: true,
          hideEdgesOnDrag: true,
        },
      }
      
      if (graphInstance.value) {
        graphInstance.value.destroy()
        graphInstance.value = null
      }
      
      if (graphContainer.value && networkDataSet.value) {
        graphInstance.value = new Network(graphContainer.value, networkDataSet.value, options)
        
        graphInstance.value.on('click', async (params: any) => {
          if (params.nodes.length > 0) {
            const tagId = parseInt(params.nodes[0])
            const tag = graphData.value.tags.find((t: GraphTag) => t.id === tagId)
            if (tag) {
              await onTagClick(tag)
            }
          } else {
            selectedTag.value = null
            selectedFileDetail.value = null
          }
        })
        
        graphInstance.value.on('doubleClick', async (params: any) => {
          if (params.nodes.length > 0) {
            const tagId = parseInt(params.nodes[0])
            const tag = graphData.value.tags.find((t: GraphTag) => t.id === tagId)
            if (tag) {
              await onTagClick(tag)
            }
          }
        })
        
        graphInstance.value.on('hoverNode', (params: any) => {
          // Highlight neighborhood
          if (params.node) {
            const neighbors = graphInstance.value?.getConnectedNodes(params.node) || []
            const highlightSet = new Set([params.node, ...neighbors])
            
            const allNodes = networkDataSet.value!.nodes.get()
            networkDataSet.value!.nodes.update(
              allNodes.map((node: any) => ({
                ...node,
                color: {
                  ...node.color,
                  opacity: highlightSet.has(node.id) ? 1 : 0.15,
                },
              }))
            )
            
            const allEdges = networkDataSet.value!.edges.get()
            networkDataSet.value!.edges.update(
              allEdges.map((edge: any) => {
                const isHighlighted = highlightSet.has(String(edge.from)) && highlightSet.has(String(edge.to))
                return {
                  ...edge,
                  color: {
                    ...edge.color,
                    opacity: isHighlighted ? 0.8 : 0.03,
                  },
                }
              })
            )
          }
        })
        
        graphInstance.value.on('blurNode', () => {
          // Reset all nodes/edges to full visibility
          const allNodes = networkDataSet.value!.nodes.get()
          networkDataSet.value!.nodes.update(
            allNodes.map((node: any) => ({
              ...node,
              color: {
                background: node.color.background,
                border: node.color.border,
                highlight: node.color.highlight,
                hover: node.color.hover,
                opacity: 1,
              },
            }))
          )
          
          const allEdges = networkDataSet.value!.edges.get()
          networkDataSet.value!.edges.update(
            allEdges.map((edge: any) => ({
              ...edge,
              color: {
                ...edge.color,
                opacity: 0.6,
              },
            }))
          )
        })
      }
    })
  }

function buildNodeTooltip(tag: GraphTag): string {
  return `${tag.name}<br>Files: ${tag.num_files}<br>Descriptions: ${tag.files_with_descriptions}`
}

async function onTagClick(tag: GraphTag) {
  selectedTag.value = tag
  
  // Reset file detail when switching tags
  selectedFileDetail.value = null
  
  // Fetch files for this tag using paginated endpoint
  await fetchTagFiles(tag.id)
}

async function fetchTagFiles(tagId: number) {
  // Check if already cached
  if (tagFilesCache.value.has(tagId) && tagFilesCache.value.get(tagId)?.length) {
    return
  }
  
  tagFilesCacheLoading.value.set(tagId, true)
  try {
    const result = await $fetch('/api/settings/rag-index/tag-files', {
      method: 'GET',
      query: { tag_id: String(tagId), limit: '200', offset: '0' },
    })
    tagFilesCache.value.set(tagId, result.files || [])
    
    // Fetch file detail for first file
    const files = result.files || []
    if (files.length > 0) {
      await fetchFileDetail(files[0].file_id)
    }
  } catch (error: any) {
    console.error(`Failed to fetch tag files for tag ${tagId}:`, error)
  } finally {
    tagFilesCacheLoading.value.set(tagId, false)
  }
}

function getTagFiles(tagId: number): TagFileMapping[] {
  return tagFilesCache.value.get(tagId) || graphData.value.tagFileMappings[tagId] || []
}

async function fetchFileDetail(fileId: string) {
  try {
    const [tagsResult, descResult] = await Promise.all([
      $fetch(`/api/settings/rag-index/file-tags?file_id=${fileId}`),
      $fetch(`/api/settings/rag-index/file-descriptions?file_id=${fileId}`),
    ])
    
    selectedFileDetail.value = {
      file_id: fileId,
      file_name: tagsResult.fileName || 'Unknown',
      preview_url: `/api/files/preview-proxy/${fileId}?x=800&y=800`,
      tags: tagsResult.tags || [],
      descriptions: descResult.descriptions || [],
    }
  } catch (error: any) {
    console.error('Failed to fetch file detail:', error)
  }
}

async function removeTagFromFile(tagId: number, fileId: string) {
  if (!confirm('Remove this tag from the file?')) return
  
  try {
    await $fetch('/api/settings/rag-index/remove-tag-mapping', {
      method: 'DELETE',
      body: { tag_id: tagId, file_id: fileId },
    })
    
    // Refresh graph data
    await fetchGraphData()
    selectedFileDetail.value = null
    selectedTag.value = null
  } catch (error: any) {
    alert(`Failed to remove tag: ${error.message || 'Unknown error'}`)
  }
}

// ========== List View Methods ==========
async function fetchListTags() {
  listLoading.value = true
  try {
    const params: Record<string, string> = {
      sort_by: listSortBy.value,
      sort_order: listSortDirection.value,
      limit: String(listPageSize),
      offset: String(listPage.value * listPageSize),
    }
    
    if (listSearchQuery.value) {
      params.search = listSearchQuery.value
    }
    if (listFilterDesc.value !== 'all') {
      params.filter_desc = listFilterDesc.value
    }
    if (listFilterColor.value !== 'all') {
      params.filter_color = listFilterColor.value
    }
    
    const result = await $fetch('/api/settings/rag-index/list-tags-with-desc-counts', {
      method: 'GET',
      query: params,
    })
    
    listTags.value = result.tags || []
    listTotal.value = result.total || 0
  } catch (error: any) {
    console.error('Failed to fetch list tags:', error)
    alert(`Failed to fetch tags: ${error.message || 'Unknown error'}`)
  } finally {
    listLoading.value = false
  }
}

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

function toggleListSort(column: 'name' | 'num_files') {
  if (listSortBy.value === column) {
    listSortDirection.value = listSortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    listSortBy.value = column
    listSortDirection.value = 'asc'
  }
  fetchListTags()
}

// ========== Descriptions View Methods ==========
async function fetchDescriptions() {
  descriptionsLoading.value = true
  try {
    const params: Record<string, string> = {
      limit: String(descriptionsPageSize),
      offset: String(descriptionsPage.value * descriptionsPageSize),
    }
    
    if (descriptionsSearchQuery.value) {
      params.search = descriptionsSearchQuery.value
    }
    if (descriptionsFilter.value !== 'all') {
      params.filter = descriptionsFilter.value
    }
    
    // Use dedicated descriptions-list endpoint
    // Response: each entry has file_id + array of descriptions for that file
    const result = await $fetch('/api/settings/rag-index/descriptions-list', {
      method: 'GET',
      query: params,
    })
    
    descriptions.value = (result.descriptions || []).map((desc: any) => ({
      file_id: desc.file_id,
      file_name: desc.file_name,
      preview_url: `/api/files/preview-proxy/${desc.file_id}?x=200&y=200`,
      descriptions: desc.descriptions || [],
    }))
    descriptionsTotal.value = result.total || 0
  } catch (error: any) {
    console.error('Failed to fetch descriptions:', error)
  } finally {
    descriptionsLoading.value = false
  }
}

async function onDescFileClick(fileId: string) {
  await fetchFileDetail(fileId)
}

// ========== Lifecycle ==========
onMounted(() => {
  fetchGraphData()
})

watch(activeTab, (newTab) => {
  if (newTab === 'list') {
    fetchListTags()
  } else if (newTab === 'descriptions') {
    fetchDescriptions()
  }
})

// Refresh handlers
function refreshGraph() {
  fetchGraphData()
}

function refreshList() {
  fetchListTags()
}

function refreshDescriptions() {
  fetchDescriptions()
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <Tag class="w-6 h-6 text-gray-600 dark:text-gray-400" />
          <div>
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Tag Management</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              Explore tags, manage file associations, and view descriptions.
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="activeTab === 'graph' ? refreshGraph() : activeTab === 'list' ? refreshList() : refreshDescriptions()"
            :disabled="isLoading || listLoading || descriptionsLoading"
            class="px-3 py-2 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw :class="{ 'animate-spin': isLoading || listLoading || descriptionsLoading }" class="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-4 gap-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">Total Tags</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-gray-100">{{ totalTags }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">Files with Tags</p>
        <p class="text-2xl font-semibold text-blue-600 dark:text-blue-400">{{ totalFilesWithTags }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">Files with Descriptions</p>
        <p class="text-2xl font-semibold text-green-600 dark:text-green-400">{{ totalFilesWithDescriptions }}</p>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
        <p class="text-sm text-gray-500 dark:text-gray-400">Total Descriptions</p>
        <p class="text-2xl font-semibold text-purple-600 dark:text-purple-400">{{ totalDescriptions }}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div class="border-b border-gray-200 dark:border-gray-700">
        <nav class="flex -mb-px">
          <button
            @click="activeTab = 'graph'"
            :class="activeTab === 'graph'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'"
            class="px-6 py-4 text-sm font-medium border-b-2 flex items-center gap-2"
          >
            <Tag class="w-4 h-4" />
            Graph View
          </button>
          <button
            @click="activeTab = 'list'"
            :class="activeTab === 'list'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'"
            class="px-6 py-4 text-sm font-medium border-b-2 flex items-center gap-2"
          >
            <Filter class="w-4 h-4" />
            List View
          </button>
          <button
            @click="activeTab = 'descriptions'"
            :class="activeTab === 'descriptions'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300'"
            class="px-6 py-4 text-sm font-medium border-b-2 flex items-center gap-2"
          >
            <FileText class="w-4 h-4" />
            Descriptions
          </button>
        </nav>
      </div>

      <!-- Graph View Tab -->
      <div v-show="activeTab === 'graph'" class="p-4">
        <div v-if="isLoading" class="flex items-center justify-center py-12">
          <RefreshCw class="w-8 h-8 animate-spin text-gray-400" />
        </div>
        <div v-else class="flex gap-4" style="height: calc(100vh - 380px); min-height: 500px;">
          <!-- Graph Container -->
          <div class="flex-1 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div ref="graphContainer" class="w-full h-full"></div>
          </div>
          
          <!-- Detail Panel -->
          <div class="w-96 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-y-auto">
            <div v-if="!selectedTag" class="p-6 text-center text-gray-400">
              <Tag class="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p class="text-sm">Click a tag in the graph to view details</p>
            </div>
            
            <div v-else class="p-4">
              <!-- Selected Tag Info -->
              <div class="mb-4">
                <div class="flex items-center gap-2 mb-2">
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ selectedTag.name }}</h3>
                </div>
                <div class="grid grid-cols-2 gap-2 text-sm">
                  <div class="text-gray-500 dark:text-gray-400">Files:</div>
                  <div class="text-gray-900 dark:text-gray-100">{{ selectedTag.num_files }}</div>
                  <div class="text-gray-500 dark:text-gray-400">With Descriptions:</div>
                  <div class="text-gray-900 dark:text-gray-100">{{ selectedTag.files_with_descriptions }}</div>
                </div>
              </div>
              
              <!-- Files List -->
              <div class="mb-4">
                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Files ({{ getTagFiles(selectedTag.id).length }})</h4>
                <div class="space-y-1 max-h-48 overflow-y-auto">
                  <button
                    v-for="mapping in getTagFiles(selectedTag.id).slice(0, 20)"
                    :key="mapping.file_id"
                    @click="fetchFileDetail(mapping.file_id)"
                    :class="selectedFileDetail?.file_id === mapping.file_id
                      ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700 border-transparent'"
                    class="w-full flex items-center gap-2 p-2 rounded border text-left text-sm transition-colors"
                  >
                    <ImageIcon class="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span class="truncate text-gray-700 dark:text-gray-300">{{ mapping.file_name }}</span>
                    <FileText v-if="mapping.has_description" class="w-3 h-3 text-green-500 ml-auto flex-shrink-0" />
                  </button>
                  <div v-if="getTagFiles(selectedTag.id).length > 20" class="text-xs text-gray-400 text-center py-2">
                    +{{ getTagFiles(selectedTag.id).length - 20 }} more files
                  </div>
                </div>
              </div>
              
              <!-- File Detail -->
              <div v-if="selectedFileDetail" class="border-t border-gray-200 dark:border-gray-700 pt-4">
                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">File Details</h4>
                
                <!-- Image Preview -->
                <div class="mb-3 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
                  <img
                    :src="selectedFileDetail.preview_url"
                    :alt="selectedFileDetail.file_name"
                    class="w-full h-40 object-cover"
                    @error="$event.target.style.display='none'"
                  />
                </div>
                
                <!-- File Name -->
                <p class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3 truncate">{{ selectedFileDetail.file_name }}</p>
                
                <!-- Tags -->
                <div class="mb-3">
                  <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Tags:</p>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="tag in selectedFileDetail.tags"
                      :key="tag.id"
                      class="px-2 py-0.5 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 flex items-center gap-1"
                    >
                      {{ tag.name }}
                      <button
                        @click.stop="removeTagFromFile(tag.id, selectedFileDetail.file_id)"
                        class="text-red-400 hover:text-red-600"
                        title="Remove tag"
                      >
                        <X class="w-3 h-3" />
                      </button>
                    </span>
                  </div>
                </div>
                
                <!-- Descriptions -->
                <div v-if="selectedFileDetail.descriptions.length > 0" class="mb-3">
                  <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Descriptions:</p>
                  <div class="space-y-2">
                    <div
                      v-for="desc in selectedFileDetail.descriptions"
                      :key="desc.id"
                      class="p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300"
                    >
                      {{ desc.description }}
                      <span v-if="desc.pinned" class="ml-2 text-xs text-yellow-600">(pinned)</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- List View Tab -->
      <div v-show="activeTab === 'list'" class="p-4">
        <!-- Search and Filters -->
        <div class="mb-4 flex flex-wrap gap-3">
          <div class="flex-1 min-w-[200px]">
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                v-model="listSearchQuery"
                type="text"
                placeholder="Search tags..."
                @input="fetchListTags()"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <select
            v-model="listFilterDesc"
            class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            @change="fetchListTags()"
          >
            <option value="all">All Files</option>
            <option value="has">Has Descriptions</option>
            <option value="none">No Descriptions</option>
          </select>
          <select
            v-model="listFilterColor"
            class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            @change="fetchListTags()"
          >
            <option value="all">All Types</option>
            <option value="true">Color Tags</option>
            <option value="false">Regular Tags</option>
          </select>
          <button
            @click="refreshList"
            :disabled="listLoading"
            class="px-3 py-2 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw :class="{ 'animate-spin': listLoading }" class="w-4 h-4" />
          </button>
        </div>
        
        <!-- Tags Table -->
        <div v-if="listLoading" class="flex items-center justify-center py-12">
          <RefreshCw class="w-8 h-8 animate-spin text-gray-400" />
        </div>
        <div v-else-if="listTags.length === 0" class="text-center py-12 text-gray-400">
          <Tag class="w-12 h-12 mx-auto mb-3" />
          <p class="text-sm">No tags found.</p>
        </div>
        <div v-else class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead class="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase w-8"></th>
                <th 
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                  @click="toggleListSort('name')"
                >
                  <div class="flex items-center gap-1">
                    Tag Name
                    <ArrowUpDown v-if="listSortBy === 'name'" class="w-3 h-3" :class="{ 'rotate-180': listSortDirection === 'desc' }" />
                  </div>
                </th>
                <th 
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
                  @click="toggleListSort('num_files')"
                >
                  <div class="flex items-center gap-1">
                    Files
                    <ArrowUpDown v-if="listSortBy === 'num_files'" class="w-3 h-3" :class="{ 'rotate-180': listSortDirection === 'desc' }" />
                  </div>
                </th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Descriptions</th>
                <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type</th>
              </tr>
            </thead>
            <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              <tr 
                v-for="tag in listTags" 
                :key="tag.id"
                :class="expandedListTag === tag.id ? 'bg-blue-50 dark:bg-blue-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-700'"
              >
                <td class="px-4 py-3">
                  <button
                    @click="fetchListTagFiles(tag.id)"
                    class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <ChevronDown v-if="expandedListTag === tag.id" class="w-4 h-4" />
                    <ChevronUp v-else class="w-4 h-4" />
                  </button>
                </td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ tag.name }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ tag.num_files }}</td>
                <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ tag.files_with_descriptions }} files</td><td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">Regular</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <!-- Expanded Tag Files -->
        <div v-if="expandedListTag !== null" class="mt-2 ml-12">
          <div v-if="listTagFilesLoading" class="flex items-center gap-2 py-2 text-sm text-gray-400">
            <RefreshCw class="w-4 h-4 animate-spin" />
            Loading files...
          </div>
          <div v-else class="space-y-1">
            <div
              v-for="file in listTagFiles"
              :key="file.file_id"
              class="flex items-center gap-2 p-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700 text-sm"
            >
              <ImageIcon class="w-4 h-4 text-gray-400" />
              <span class="text-gray-700 dark:text-gray-300">{{ file.file_name }}</span>
              <FileText v-if="file.has_description" class="w-3 h-3 text-green-500" />
            </div>
          </div>
        </div>
        
        <!-- Pagination -->
        <div v-if="listTotal > listPageSize" class="flex items-center justify-between mt-4">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Showing {{ listPage * listPageSize + 1 }} to {{ Math.min((listPage + 1) * listPageSize, listTotal) }} of {{ listTotal }} tags
          </p>
          <div class="flex gap-2">
            <button
              @click="listPage = Math.max(0, listPage - 1)"
              :disabled="listPage === 0"
              class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              @click="listPage = Math.min(Math.ceil(listTotal / listPageSize) - 1, listPage + 1)"
              :disabled="listPage >= Math.ceil(listTotal / listPageSize) - 1"
              class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <!-- Descriptions Tab -->
      <div v-show="activeTab === 'descriptions'" class="p-4">
        <!-- Search and Filters -->
        <div class="mb-4 flex flex-wrap gap-3">
          <div class="flex-1 min-w-[200px]">
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                v-model="descriptionsSearchQuery"
                type="text"
                placeholder="Search files or descriptions..."
                @input="fetchDescriptions()"
                class="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
          <select
            v-model="descriptionsFilter"
            class="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            @change="fetchDescriptions()"
          >
            <option value="all">All Files</option>
            <option value="has">Has Description</option>
            <option value="none">No Description</option>
          </select>
          <button
            @click="refreshDescriptions"
            :disabled="descriptionsLoading"
            class="px-3 py-2 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw :class="{ 'animate-spin': descriptionsLoading }" class="w-4 h-4" />
          </button>
        </div>
        
        <!-- Descriptions List -->
        <div v-if="descriptionsLoading" class="flex items-center justify-center py-12">
          <RefreshCw class="w-8 h-8 animate-spin text-gray-400" />
        </div>
        <div v-else-if="descriptions.length === 0" class="text-center py-12 text-gray-400">
          <FileText class="w-12 h-12 mx-auto mb-3" />
          <p class="text-sm">No descriptions found.</p>
        </div>
        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="desc in descriptions"
            :key="desc.file_id"
            @click="onDescFileClick(desc.file_id)"
            class="bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden cursor-pointer hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
            :class="selectedDescFileDetail?.file_id === desc.file_id ? 'border-blue-400 dark:border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800' : ''"
          >
            <!-- Thumbnail -->
            <div class="h-32 bg-gray-200 dark:bg-gray-600 overflow-hidden">
              <img
                :src="desc.preview_url"
                :alt="desc.file_name"
                class="w-full h-full object-cover"
                @error="$event.target.style.display='none'"
              />
            </div>
            <!-- Content -->
            <div class="p-3">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate mb-2">{{ desc.file_name }}</p>
              <!-- All descriptions for this file -->
              <div class="space-y-2">
                <div
                  v-for="d in desc.descriptions"
                  :key="d.id"
                  class="text-xs text-gray-500 dark:text-gray-400"
                >
                  <span v-if="d.pinned" class="text-yellow-600 dark:text-yellow-400 font-medium mr-1">📌</span>
                  <span class="line-clamp-3">{{ d.description }}</span>
                </div>
              </div>
              <div class="flex items-center gap-2 mt-2">
                <ZoomIn class="w-3 h-3 text-gray-400" />
                <span class="text-xs text-gray-400">Click to view details</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Pagination -->
        <div v-if="descriptionsTotal > descriptionsPageSize" class="flex items-center justify-between mt-4">
          <p class="text-sm text-gray-500 dark:text-gray-400">
            Showing {{ descriptionsPage * descriptionsPageSize + 1 }} to {{ Math.min((descriptionsPage + 1) * descriptionsPageSize, descriptionsTotal) }} of {{ descriptionsTotal }}
          </p>
          <div class="flex gap-2">
            <button
              @click="descriptionsPage = Math.max(0, descriptionsPage - 1)"
              :disabled="descriptionsPage === 0"
              class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              @click="descriptionsPage = Math.min(Math.ceil(descriptionsTotal / descriptionsPageSize) - 1, descriptionsPage + 1)"
              :disabled="descriptionsPage >= Math.ceil(descriptionsTotal / descriptionsPageSize) - 1"
              class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- File Detail Modal (for descriptions tab) -->
    <Teleport to="body">
      <div v-if="selectedDescFileDetail && activeTab === 'descriptions'" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" @click.self="selectedDescFileDetail = null">
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
          <div class="p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ selectedDescFileDetail.file_name }}</h3>
              <button
                @click="selectedDescFileDetail = null"
                class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
            
            <!-- Image Preview -->
            <div class="mb-4 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700">
              <img
                :src="selectedDescFileDetail.preview_url"
                :alt="selectedDescFileDetail.file_name"
                class="w-full h-64 object-cover"
                @error="$event.target.style.display='none'"
              />
            </div>
            
            <!-- Tags -->
            <div class="mb-4">
              <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tags:</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="tag in selectedDescFileDetail.tags"
                  :key="tag.id"
                  class="px-3 py-1 text-sm rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 flex items-center gap-1"
                >
                  {{ tag.name }}
                  <button
                    @click.stop="removeTagFromFile(tag.id, selectedDescFileDetail.file_id)"
                    class="text-red-400 hover:text-red-600"
                    title="Remove tag"
                  >
                    <X class="w-3 h-3" />
                  </button>
                </span>
              </div>
            </div>
            
            <!-- Descriptions -->
            <div v-if="selectedDescFileDetail.descriptions.length > 0">
              <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Descriptions:</p>
              <div class="space-y-2">
                <div
                  v-for="desc in selectedDescFileDetail.descriptions"
                  :key="desc.id"
                  class="p-3 bg-gray-50 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300"
                >
                  {{ desc.description }}
                  <span v-if="desc.pinned" class="ml-2 text-xs text-yellow-600">(pinned)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
