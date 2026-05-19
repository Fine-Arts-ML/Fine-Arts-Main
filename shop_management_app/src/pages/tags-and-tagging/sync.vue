<script setup lang="ts">
import { useAuth } from '~/composables/useAuth'
import { useImagePreview } from '~/composables/useImagePreview'
import ImagePreviewModal from '~/components/ImagePreviewModal.vue'
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
  ZoomIn,
  ZoomOut,
  Pin,
  PinOff,
  Plus,
  Send,
  ArrowUpDown
} from 'lucide-vue-next'

const { isAdmin, isAuthenticated } = useAuth()

// ========== Image Preview ==========
const { open: openPreview, close: closePreview, navigate: navigatePreview, state: previewState } = useImagePreview()

// ========== Custom Description Input State ==========
const showCustomDescriptionInput = ref(false)
const newCustomDescription = ref('')
const isCreatingDescription = ref(false)

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

interface FileTag {
  id: number
  name: string
  color: string
}

interface FileDetail {
  file_id: string
  file_name: string
  preview_url: string
  tags: FileTag[]
  descriptions: Array<{ id: number; description: string; pinned: boolean; createdAt: string }>
}

interface ListTag {
  id: number
  name: string
  num_files: number
  files_with_descriptions: number
}

// ========== Cluster Types ==========
interface ClusterFileNode {
  id: string
  file_id: string
  file_name: string
  clusterId: number
  tags: { id: number; name: string }[]
  has_description: boolean
  isOrphan?: boolean
}

interface TagCluster {
  clusterId: number
  name: string
  color: string
  dominantTags: { id: number; name: string }[]
  fileCount: number
}

interface ClusterEdge {
  sourceCluster: number
  targetCluster: number
  sharedTags: { id: number; name: string; count: number }[]
  totalSharedFiles: number
}

interface ClusterGraphData {
  clusters: TagCluster[]
  clusterEdges: ClusterEdge[]
  fileNodes: ClusterFileNode[]
  orphanFiles: ClusterFileNode[]
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

// Cluster view state
const clusterGraphData = ref<ClusterGraphData | null>(null)
const clusterColors = [
  '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
  '#9c755d', '#bab0ac', '#d37295', '#nepd85', '#7c9ab1', '#e67a38', '#8cbf86', '#e87cb8'
] as const

// Track which view mode we're in
const graphViewMode = ref<'tags' | 'clusters'>('clusters')

// Selected cluster for detail panel
const selectedCluster = ref<TagCluster | null>(null)

// Drill-down state
const isDrillDown = ref(false)
const drilledClusterId = ref<number | null>(null)

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
const listTagFiles = ref<Array<{ file_id: string; file_name: string; has_description: boolean; preview_url?: string }>>([])
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

// ========== Clustering Algorithm ==========

/**
 * Compute tag clusters using label propagation on the tag co-occurrence graph.
 * Files are then assigned to clusters based on their dominant tags.
 */
function computeTagClusters(): ClusterGraphData {
  const { tags, edges, tagFileMappings } = graphData.value
  
  if (tags.length === 0 || edges.length === 0) {
    return { clusters: [], clusterEdges: [], fileNodes: [], orphanFiles: [] }
  }
  
  // Build adjacency list with weights - only strong connections
  const adjacency = new Map<number, Map<number, number>>()
  const tagSet = new Set(tags.map((t: GraphTag) => t.id))
  
  // ========== HUB TAG REMOVAL FOR CLUSTERING ==========
  // Generic tags (e.g., "abstract", "modern", "colorful") act as hubs connecting everything
  // This causes label propagation to converge to one dominant cluster
  // Solution: Remove hub tags from clustering graph, assign them after
  
  // Calculate tag frequency percentile to identify hubs
  const tagFileCounts = tags.map((t: GraphTag) => t.num_files).sort((a, b) => a - b)
  const p90FileCount = tagFileCounts[Math.floor(tagFileCounts.length * 0.9)] // 90th percentile threshold
  
  // Identify hub tags (tags that appear in too many files)
  const hubTagIds = new Set<number>()
  const nonHubTags = new Set<number>()
  for (const tag of tags) {
    if (tag.num_files > p90FileCount) {
      hubTagIds.add(tag.id)
    } else {
      nonHubTags.add(tag.id)
    }
  }
  
  console.log('[CLUSTER DEBUG] Hub tag threshold (p90):', p90FileCount, 'files | Hub tags:', hubTagIds.size, '| Non-hub tags:', nonHubTags.size)
  
  // Only consider edges with at least 1 shared file
  const MIN_SHARED_FILES = 1
  
  for (const edge of edges) {
    if (!tagSet.has(edge.tag_id_1) || !tagSet.has(edge.tag_id_2)) continue
    if (edge.shared_files < MIN_SHARED_FILES) continue
    
    if (!adjacency.has(edge.tag_id_1)) adjacency.set(edge.tag_id_1, new Map())
    if (!adjacency.has(edge.tag_id_2)) adjacency.set(edge.tag_id_2, new Map())
    
    const currentWeight1 = adjacency.get(edge.tag_id_1)?.get(edge.tag_id_2) ?? 0
    const currentWeight2 = adjacency.get(edge.tag_id_2)?.get(edge.tag_id_1) ?? 0
    adjacency.get(edge.tag_id_1)!.set(edge.tag_id_2, currentWeight1 + edge.shared_files)
    adjacency.get(edge.tag_id_2)!.set(edge.tag_id_1, currentWeight2 + edge.shared_files)
  }
  
  // Remove hub tags from adjacency list (but keep track of their connections)
  for (const hubId of hubTagIds) {
    adjacency.delete(hubId)
    // Remove hub from other nodes' neighbor lists
    for (const [tagId, neighbors] of adjacency.entries()) {
      neighbors.delete(hubId)
    }
  }
  
  // DIAGNOSTIC: Count tags with neighbors after hub removal
  const tagsWithNeighbors = new Set<number>()
  for (const [tagId, neighbors] of adjacency.entries()) {
    if (neighbors.size > 0) {
      tagsWithNeighbors.add(tagId)
      for (const neighborId of neighbors.keys()) {
        tagsWithNeighbors.add(neighborId)
      }
    }
  }
  const tagsWithoutNeighbors = nonHubTags.size - tagsWithNeighbors.size
  console.log('[CLUSTER DEBUG] Non-hub tags with neighbors:', tagsWithNeighbors.size, '| Non-hub tags without neighbors:', tagsWithoutNeighbors)
  
  // Label propagation for community detection - only on non-hub tags
  const labels = new Map<number, number>()
  tags.forEach((tag: GraphTag) => labels.set(tag.id, tag.id)) // Initial: each node has unique label
  
  const maxIterations = 15 // More iterations for better cluster assignment
  for (let iter = 0; iter < maxIterations; iter++) {
    let changed = false
    // Only shuffle non-hub tags for label propagation
    const nonHubTagList = tags.filter((t: GraphTag) => nonHubTags.has(t.id))
    const shuffledTags = nonHubTagList.sort(() => Math.random() - 0.5)
    
    for (const tag of shuffledTags) {
      const neighborWeights = new Map<number, number>()
      const neighbors = adjacency.get(tag.id)
      if (!neighbors) continue
      
      let totalWeight = 0
      for (const [neighborId, weight] of neighbors.entries()) {
        const neighborLabel = labels.get(neighborId)
        if (neighborLabel) {
          neighborWeights.set(neighborLabel, (neighborWeights.get(neighborLabel) ?? 0) + weight)
          totalWeight += weight
        }
      }
      
      if (neighborWeights.size === 0) continue
      
      // Find best label - require significant margin over second best
      const sortedLabels = [...neighborWeights.entries()].sort((a, b) => b[1] - a[1])
      const bestLabel = sortedLabels[0][0]
      const bestWeight = sortedLabels[0][1]
      const secondBestWeight = sortedLabels.length > 1 ? sortedLabels[1][1] : 0
      
      // Only switch if best is at least 50% better than current and significantly better than second best
      const currentLabel = labels.get(tag.id) ?? tag.id
      const currentWeight = neighborWeights.get(currentLabel) ?? 0
      
      const marginRequired = Math.max(totalWeight * 0.15, 1) // Need 15% margin or at least 1 vote (relaxed)
      if (bestWeight > currentWeight) {
        labels.set(tag.id, bestLabel)
        changed = true
      }
    }
    
    if (!changed) break
  }
  
  // ========== ASSIGN HUB TAGS TO CLUSTERS ==========
  // Hub tags are assigned to clusters based on their strongest connection to non-hub tags
  for (const hubTag of tags) {
    if (hubTagIds.has(hubTag.id) === false) continue // Skip non-hub tags
    
    const hubNeighbors = adjacency.get(hubTag.id)
    if (!hubNeighbors || hubNeighbors.size === 0) {
      // Hub with no neighbors gets its own cluster label
      labels.set(hubTag.id, hubTag.id)
      continue
    }
    
    // Find the dominant label among hub's non-hub neighbors
    const neighborLabelWeights = new Map<number, number>()
    for (const [neighborId, weight] of hubNeighbors.entries()) {
      if (hubTagIds.has(neighborId)) continue // Skip hub neighbors
      const neighborLabel = labels.get(neighborId)
      if (neighborLabel != null) {
        neighborLabelWeights.set(neighborLabel, (neighborLabelWeights.get(neighborLabel) ?? 0) + weight)
      }
    }
    
    if (neighborLabelWeights.size > 0) {
      const bestLabel = [...neighborLabelWeights.entries()].sort((a, b) => b[1] - a[1])[0][0]
      labels.set(hubTag.id, bestLabel)
    } else {
      labels.set(hubTag.id, hubTag.id)
    }
  }
  
  console.log('[CLUSTER DEBUG] Hub tags assigned to clusters')
  
  // Group tags by cluster (label)
  const clusterTagMap = new Map<number, number[]>()
  for (const [tagId, clusterLabel] of labels.entries()) {
    if (!clusterTagMap.has(clusterLabel)) clusterTagMap.set(clusterLabel, [])
    clusterTagMap.get(clusterLabel)!.push(tagId)
  }
  
  // Build cluster info - only keep meaningful clusters
  const tagById = new Map(tags.map(t => [t.id, t]))
  const clusters: TagCluster[] = []
  
  // Calculate average files per tag for threshold
  const avgFilesPerTag = tags.reduce((sum, t) => sum + t.num_files, 0) / Math.max(tags.length, 1)
  // Very low threshold to preserve even small clusters - only filter truly empty clusters
  const MIN_CLUSTER_SIZE = 2 // Minimum 2 files per cluster
  
  // DIAGNOSTIC: Log cluster sizes before filtering
  const preFilterClusters = [...clusterTagMap.entries()].map(([id, tagIds]) => ({
    clusterId: id,
    tagCount: tagIds.length,
    sampleTags: tagIds.slice(0, 5).map(id => tagById.get(id)?.name ?? '?')
  })).sort((a, b) => b.tagCount - a.tagCount)
  console.log('[CLUSTER DEBUG] Pre-filter clusters:', preFilterClusters.length, '| avgFilesPerTag:', avgFilesPerTag.toFixed(1), '| MIN_CLUSTER_SIZE:', MIN_CLUSTER_SIZE)
  preFilterClusters.slice(0, 10).forEach((c, i) => console.log(`  [CLUSTER DEBUG]   Cluster ${i}: ${c.tagCount} tags, sample: ${c.sampleTags.join(', ')}`))
  
  for (const [clusterId, tagIds] of clusterTagMap.entries()) {
    if (tagIds.length < 1) continue
    
    // Find dominant tags (top 3 by file count)
    const tagFileCounts = tagIds.map((id: number) => ({
      id,
      name: tagById.get(id)?.name ?? '',
      fileCount: tagById.get(id)?.num_files ?? 0
    })).sort((a, b) => b.fileCount - a.fileCount)
    
    const dominantTags = tagFileCounts.slice(0, 3)
    const name = dominantTags[0]?.name ?? `Cluster ${clusterId}`
    
    // Count unique files in this cluster
    const fileSet = new Set<string>()
    for (const tagId of tagIds) {
      const files = tagFileMappings[tagId]
      if (files) {
        files.forEach((f: TagFileMapping) => fileSet.add(f.file_id))
      }
    }
    
    // Only include clusters with meaningful size
    if (fileSet.size < MIN_CLUSTER_SIZE) {
      console.log('[CLUSTER DEBUG] FILTERED cluster with', tagIds.length, 'tags, fileSet.size:', fileSet.size, '(MIN_CLUSTER_SIZE:', MIN_CLUSTER_SIZE, ')')
      continue
    }
    
    clusters.push({
      clusterId,
      name,
      color: clusterColors[clusters.length % clusterColors.length],
      dominantTags: dominantTags.map(d => ({ id: d.id, name: d.name })),
      fileCount: fileSet.size
    })
  }
  
  // Sort clusters by file count descending
  clusters.sort((a, b) => b.fileCount - a.fileCount)
  
  // Reassign cluster IDs for consistent ordering
  const oldToNewClusterId = new Map<number, number>()
  clusters.forEach((c, i) => {
    oldToNewClusterId.set(c.clusterId, i)
    c.clusterId = i
  })
  
  // Create file nodes - only for files in meaningful clusters
  const fileNodeMap = new Map<string, ClusterFileNode>()
  
  for (const [tagIdStr, fileMappings] of Object.entries(tagFileMappings)) {
    const tagIdNum = parseInt(tagIdStr)
    const originalClusterId = labels.get(tagIdNum)
    if (originalClusterId == null) continue
    
    const newClusterId = oldToNewClusterId.get(originalClusterId)
    if (newClusterId == null) continue // Skip tags not in any valid cluster
    
    const tagInfo = tagById.get(tagIdNum)
    if (!tagInfo) continue
    
    for (const mapping of fileMappings) {
      if (fileNodeMap.has(mapping.file_id)) continue
      
      fileNodeMap.set(mapping.file_id, {
        id: `file-${mapping.file_id}`,
        file_id: mapping.file_id,
        file_name: mapping.file_name,
        clusterId: newClusterId,
        tags: [{ id: tagInfo.id, name: tagInfo.name }],
        has_description: mapping.has_description
      })
    }
  }
  
  // For files with multiple tags across clusters, assign to strongest cluster
  const fileClusterWeights = new Map<string, Map<number, number>>()
  for (const [tagIdStr, fileMappings] of Object.entries(tagFileMappings)) {
    const tagIdNum = parseInt(tagIdStr)
    const originalClusterId = labels.get(tagIdNum)
    if (originalClusterId == null) continue
    const newClusterId = oldToNewClusterId.get(originalClusterId)
    if (newClusterId == null) continue
    
    for (const mapping of fileMappings) {
      if (!fileClusterWeights.has(mapping.file_id)) {
        fileClusterWeights.set(mapping.file_id, new Map())
      }
      const clusterMap = fileClusterWeights.get(mapping.file_id)!
      clusterMap.set(newClusterId, (clusterMap.get(newClusterId) ?? 0) + 1)
    }
  }
  
  // Update file nodes to their strongest cluster (require clear winner)
  for (const [fileId, clusterMap] of fileClusterWeights.entries()) {
    const sortedClusters = [...clusterMap.entries()].sort((a, b) => b[1] - a[1])
    if (sortedClusters.length === 0) continue
    
    const bestCluster = sortedClusters[0][0]
    const bestWeight = sortedClusters[0][1]
    const secondWeight = sortedClusters.length > 1 ? sortedClusters[1][1] : 0
    
    // Only assign if clear winner (at least 2x the second best)
    if (sortedClusters.length === 1 || bestWeight >= secondWeight * 1.5) {
      const fileNode = fileNodeMap.get(fileId)
      if (fileNode) {
        fileNode.clusterId = bestCluster
      }
    }
  }
  
  // Enrich file nodes with all their tags (from same cluster only)
  for (const [tagIdStr, fileMappings] of Object.entries(tagFileMappings)) {
    const tagIdNum = parseInt(tagIdStr)
    const tagInfo = tagById.get(tagIdNum)
    if (!tagInfo) continue
    
    const originalClusterId = labels.get(tagIdNum)
    const newClusterId = originalClusterId != null ? oldToNewClusterId.get(originalClusterId) : undefined
    if (newClusterId == null) continue
    
    for (const mapping of fileMappings) {
      const fileNode = fileNodeMap.get(mapping.file_id)
      if (fileNode && fileNode.clusterId === newClusterId) {
        // Add tag if not already present
        if (!fileNode.tags.some((t: { id: number }) => t.id === tagIdNum)) {
          fileNode.tags.push({ id: tagIdNum, name: tagInfo.name })
        }
      }
    }
  }
  
  const fileNodes = Array.from(fileNodeMap.values())
  
  // ========== FIX: Orphan file assignment ==========
  // Orphan tags = tags whose cluster was filtered out (not tags with no edges)
  // Tags that are in edges but whose cluster didn't meet MIN_CLUSTER_SIZE are orphans
  const orphanFiles: ClusterFileNode[] = []
  const assignedFileIds = new Set<string>()
  fileNodes.forEach(f => assignedFileIds.add(f.file_id))
  
  // Build a set of valid cluster labels (labels that survived filtering)
  const validClusterLabels = new Set<number>()
  for (const cluster of clusters) {
    // Find the original label that maps to this cluster
    for (const [oldLabel, newLabel] of oldToNewClusterId) {
      if (newLabel === cluster.clusterId) {
        validClusterLabels.add(oldLabel)
        break
      }
    }
  }
  
  for (const [tagIdStr, fileMappings] of Object.entries(tagFileMappings)) {
    const tagIdNum = parseInt(tagIdStr)
    
    // Check if this tag's cluster was filtered out
    const originalClusterLabel = labels.get(tagIdNum)
    if (originalClusterLabel == null) continue // Tag had no neighbors at all
    
    const newClusterId = oldToNewClusterId.get(originalClusterLabel)
    if (newClusterId != null) continue // Tag's cluster survived filtering, files already assigned
    
    // This tag's cluster was filtered out - it's an orphan
    const tagInfo = tagById.get(tagIdNum)
    if (!tagInfo) continue
    
    // Find the best cluster for this orphan tag based on weighted edge similarity
    let bestClusterId: number | null = null
    let bestScore = 0
    
    for (const edge of edges) {
      let otherTagId: number | null = null
      if (edge.tag_id_1 === tagIdNum) {
        otherTagId = edge.tag_id_2
      } else if (edge.tag_id_2 === tagIdNum) {
        otherTagId = edge.tag_id_1
      }
      
      if (otherTagId == null) continue
      
      const otherClusterLabel = labels.get(otherTagId)
      if (otherClusterLabel == null) continue
      
      const otherNewClusterId = oldToNewClusterId.get(otherClusterLabel)
      if (otherNewClusterId == null) continue
      
      // Use weighted score for better assignment
      const score = edge.shared_files
      if (score > bestScore) {
        bestScore = score
        bestClusterId = otherNewClusterId
      }
    }
    
    // If no cluster found via edges, assign to largest cluster
    if (bestClusterId == null && clusters.length > 0) {
      bestClusterId = clusters[0].clusterId
      bestScore = 1
    }
    
    for (const mapping of fileMappings) {
      if (assignedFileIds.has(mapping.file_id)) continue
      
      assignedFileIds.add(mapping.file_id)
      
      orphanFiles.push({
        id: `file-${mapping.file_id}`,
        file_id: mapping.file_id,
        file_name: mapping.file_name,
        clusterId: bestClusterId!,
        tags: [{ id: tagInfo.id, name: tagInfo.name }],
        has_description: mapping.has_description,
        isOrphan: true
      })
    }
  }
  
  // Compute inter-cluster edges - only strong connections
  const clusterEdgeMap = new Map<string, { sourceCluster: number; targetCluster: number; sharedTags: Map<number, number>; totalSharedFiles: Set<string> }>()
  
  for (const edge of edges) {
    if (edge.shared_files < MIN_SHARED_FILES) continue
    
    const cluster1 = labels.get(edge.tag_id_1)
    const cluster2 = labels.get(edge.tag_id_2)
    if (cluster1 == null || cluster2 == null) continue
    
    const newCluster1 = oldToNewClusterId.get(cluster1)
    const newCluster2 = oldToNewClusterId.get(cluster2)
    if (newCluster1 == null || newCluster2 == null) continue
    
    if (newCluster1 === newCluster2) continue // Same cluster, skip
    
    const source = Math.min(newCluster1, newCluster2)
    const target = Math.max(newCluster1, newCluster2)
    const key = `${source}-${target}`
    
    if (!clusterEdgeMap.has(key)) {
      clusterEdgeMap.set(key, {
        sourceCluster: source,
        targetCluster: target,
        sharedTags: new Map(),
        totalSharedFiles: new Set()
      })
    }
    
    const clusterEdge = clusterEdgeMap.get(key)!
    clusterEdge.sharedTags.set(edge.tag_id_1, (clusterEdge.sharedTags.get(edge.tag_id_1) ?? 0) + edge.shared_files)
    clusterEdge.sharedTags.set(edge.tag_id_2, (clusterEdge.sharedTags.get(edge.tag_id_2) ?? 0) + edge.shared_files)
    
    // Count files that have both tags
    const files1 = new Set(tagFileMappings[edge.tag_id_1]?.map((f: TagFileMapping) => f.file_id) ?? [])
    const files2 = new Set(tagFileMappings[edge.tag_id_2]?.map((f: TagFileMapping) => f.file_id) ?? [])
    const sharedFiles = [...files1].filter(f => files2.has(f))
    sharedFiles.forEach(f => clusterEdge.totalSharedFiles.add(f))
  }
  
  const clusterEdges: ClusterEdge[] = []
  for (const [, edgeData] of clusterEdgeMap.entries()) {
    clusterEdges.push({
      sourceCluster: edgeData.sourceCluster,
      targetCluster: edgeData.targetCluster,
      sharedTags: [...edgeData.sharedTags.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
        .map(([tagId, count]) => {
          const tag = tagById.get(tagId)
          return { id: tagId, name: tag?.name ?? `Tag ${tagId}`, count }
        }),
      totalSharedFiles: edgeData.totalSharedFiles.size
    })
  }
  
  clusterEdges.sort((a, b) => b.totalSharedFiles - a.totalSharedFiles)
  
  return {
    clusters,
    clusterEdges,
    fileNodes,
    orphanFiles
  }
}

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
    
    // Compute clusters from the graph data
    clusterGraphData.value = computeTagClusters()
    
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
    if (!graphContainer.value) return
    
    // Destroy existing network
    if (graphInstance.value) {
      graphInstance.value.destroy()
      graphInstance.value = null
    }
    
    // Use clustered view by default
    const useClusters = graphViewMode.value === 'clusters'
    const clusters = clusterGraphData.value?.clusters ?? []
    const fileNodes = clusterGraphData.value?.fileNodes ?? []
    const orphanFiles = clusterGraphData.value?.orphanFiles ?? []
    
    if (useClusters && clusters.length > 0 && (fileNodes.length > 0 || orphanFiles.length > 0)) {
      renderClusteredNetwork(Network, DataSet, clusters, fileNodes, orphanFiles)
    } else {
      renderTagNetwork(Network, DataSet)
    }
  })
}

function renderClusteredNetwork(Network: any, DataSet: any, clusters: TagCluster[], fileNodes: ClusterFileNode[], orphanFiles: ClusterFileNode[] = []) {
  // ========== KNOWLEDGE GRAPH STYLE VISUALIZATION ==========
  // - Cluster centroids start at center, positioned by physics engine
  // - Only cluster centroids + inter-cluster edges shown initially
  // - File nodes shown dynamically on cluster click
  
  const clusterPositions = new Map<number, { x: number; y: number }>()
  
  // Initialize all cluster positions at center - physics will spread them organically
  clusters.forEach((cluster) => {
    clusterPositions.set(cluster.clusterId, { x: 0, y: 0 })
  })
  
  // ========== ADD ONLY CLUSTER CENTROID NODES (no file nodes yet) ==========
  const allNodes: any[] = []
  
  clusters.forEach((cluster) => {
    allNodes.push({
      id: `cluster-${cluster.clusterId}`,
      clusterId: cluster.clusterId,
      isClusterNode: true,
      shape: 'dot',
      size: 25,
      color: {
        background: cluster.color,
        border: cluster.color,
        opacity: 0.3,
      },
      font: {
        size: 12,
        face: 'Inter, system-ui, sans-serif',
        color: cluster.color,
        bold: true,
      },
      label: cluster.name,
      x: 0,
      y: 0,
      fixed: false, // Let physics position this node
      physics: true, // Enable physics for organic positioning
      title: buildClusterTooltip(cluster),
      shadow: {
        enabled: true,
        width: 6,
        x: 3,
        y: 3,
        color: `${cluster.color}50`,
      },
      borderWidth: 2,
      borderColor: cluster.color,
    })
  })
  
  const nodesDataSet = new DataSet(allNodes)
  
  // Create inter-cluster edges
  const clusterEdgesData = clusterGraphData.value?.clusterEdges ?? []
  
  const edgeData: any[] = []
  clusterEdgesData
    .filter(e => e.totalSharedFiles >= 1)
    .slice(0, 40) // Show strongest connections
    .forEach((edge, idx) => {
      const sourceCluster = clusters.find(c => c.clusterId === edge.sourceCluster)
      const targetCluster = clusters.find(c => c.clusterId === edge.targetCluster)
      if (!sourceCluster || !targetCluster) return
      
      edgeData.push({
        id: `cluster-edge-${idx}`,
        from: `cluster-${edge.sourceCluster}`,
        to: `cluster-${edge.targetCluster}`,
        width: Math.min(4, Math.max(0.8, edge.totalSharedFiles * 0.2)),
        color: {
          color: `${sourceCluster.color}50`,
          opacity: 0.25,
        },
        title: `${edge.totalSharedFiles} shared file(s): ${edge.sharedTags.map((t: any) => t.name).join(', ')}`,
        smooth: { type: 'curvedCounterClockwise', roundness: 0.15 },
        physics: true,
      })
    })
  
  const edgesDataSet = new DataSet(edgeData)
  networkDataSet.value = { nodes: nodesDataSet, edges: edgesDataSet }
  
  // ========== PHYSICS CONFIGURATION FOR FORCE-DIRECTED LAYOUT ==========
  const options = {
    nodes: {
      shape: 'dot',
      scaling: {
        min: 5,
        max: 40,
      },
      font: {
        size: 12,
        face: 'Inter, system-ui, sans-serif',
      },
      borderWidth: 1,
      shadow: {
        enabled: true,
        size: 3,
        x: 2,
        y: 2,
        color: 'rgba(0,0,0,0.25)',
      },
    },
    physics: {
      enabled: true,
      stabilization: {
        iterations: 300,
        fit: true,
        onUpdate: (params: any) => {
          // Disable physics after stabilization completes to prevent twitching on hover
          if (params.iteration === params.total) {
            graphInstance.value?.setOptions({ physics: { enabled: false } })
          }
        },
      },
      barnesHut: {
        gravitationalConstant: -800, // Stronger repulsion for better spread
        springConstant: 0.0005, // Weaker spring for more organic layout
        springLength: 250, // Longer spring length for wider spread
        damping: 0.4,
      },
    },
    interaction: {
      hover: false, // Disable built-in hover to prevent twitching; we use custom hoverNode handler
      tooltipDelay: 150,
      dragNodes: true,
      dragView: true,
      zoomView: true,
      hideEdgesOnDrag: false,
      hideEdgesOnZoom: false,
    },
    clickToUse: false,
  }
  
  graphInstance.value = new Network(graphContainer.value, networkDataSet.value, options)
  
  // ========== HELPER: Show file nodes for a cluster ==========
  const showFileNodesForCluster = (clusterId: number, centroidX: number, centroidY: number) => {
    console.log('[SHOW-FILES] clusterId:', clusterId, 'centroid:', { centroidX, centroidY })
    
    const goldenAngle = Math.PI * (3 - Math.sqrt(5))
    const maxClusterRadius = 150
    
    // Get file nodes for this cluster
    const clusterFileNodes = fileNodes.filter(f => f.clusterId === clusterId)
    const clusterOrphanNodes = orphanFiles.filter(f => f.clusterId === clusterId)
    const cluster = clusters.find(c => c.clusterId === clusterId)
    const color = cluster?.color ?? '#999'
    
    console.log('[SHOW-FILES] clusterFileNodes:', clusterFileNodes.length, 'clusterOrphanNodes:', clusterOrphanNodes.length)
    
    const newFileNodes: any[] = []
    
    // Add regular file nodes
    clusterFileNodes.forEach((file, fileIndex) => {
      const r = Math.sqrt(fileIndex / Math.max(clusterFileNodes.length, 1)) * maxClusterRadius
      const angle = fileIndex * goldenAngle + (clusterId * 0.1)
      
      newFileNodes.push({
        id: file.id,
        file_id: file.file_id,
        file_name: file.file_name,
        clusterId,
        isFileNode: true,
        isOrphanFile: false,
        shape: 'dot',
        size: 4,
        color: {
          background: color,
          border: color,
          opacity: 0.8,
        },
        font: { size: 0 },
        shadow: false,
        title: buildFileTooltip(file, clusters),
        borderWidth: 1,
        borderColor: color,
        x: centroidX + Math.cos(angle) * r,
        y: centroidY + Math.sin(angle) * r,
        fixed: true,
      })
    })
    
    // Add orphan file nodes
    clusterOrphanNodes.forEach((file, fileIndex) => {
      const r = Math.sqrt(fileIndex / Math.max(clusterOrphanNodes.length, 1)) * (maxClusterRadius + 30)
      const angle = fileIndex * goldenAngle + (clusterId * 0.15)
      
      newFileNodes.push({
        id: file.id,
        file_id: file.file_id,
        file_name: file.file_name,
        clusterId,
        isFileNode: true,
        isOrphanFile: true,
        shape: 'dot',
        size: 3,
        color: {
          background: color,
          border: color,
          opacity: 0.6,
        },
        font: { size: 0 },
        shadow: false,
        title: `${file.file_name}\nTags: ${file.tags.map(t => t.name).join(', ')}\nCluster: ${cluster?.name || 'Unknown'}`,
        borderWidth: 1,
        borderColor: color,
        x: centroidX + Math.cos(angle) * r,
        y: centroidY + Math.sin(angle) * r,
        fixed: true,
      })
    })
    
    console.log('[SHOW-FILES] newFileNodes to add:', newFileNodes.length)
    
    if (newFileNodes.length > 0) {
      // Check for existing nodes with same IDs
      const existingNodes = nodesDataSet.get()
      const existingIds = new Set(existingNodes.map((n: any) => n.id))
      const duplicateIds = newFileNodes.filter((n: any) => existingIds.has(n.id)).map((n: any) => n.id)
      
      if (duplicateIds.length > 0) {
        console.warn('[SHOW-FILES] Duplicate IDs found:', duplicateIds.length, 'IDs:', duplicateIds.slice(0, 5))
        // Remove duplicates from newFileNodes
        const cleanFileNodes = newFileNodes.filter((n: any) => !existingIds.has(n.id))
        console.log('[SHOW-FILES] After removing duplicates:', cleanFileNodes.length)
        nodesDataSet.add(cleanFileNodes)
      } else {
        nodesDataSet.add(newFileNodes)
        console.log('[SHOW-FILES] Added successfully')
      }
    }
  }
  
  // ========== HELPER: Clear file nodes for a cluster ==========
  const clearFileNodesForCluster = (clusterId: number) => {
    const currentNodes = nodesDataSet.get()
    const nodesToRemove = currentNodes.filter((n: any) =>
      (n.isFileNode && n.clusterId === clusterId)
    )
    if (nodesToRemove.length > 0) {
      nodesDataSet.remove(nodesToRemove.map(n => n.id))
    }
  }
  
  // ========== HELPER: Clear ALL file nodes ==========
  const clearAllFileNodes = () => {
    const currentNodes = nodesDataSet.get()
    const fileNodesToRemove = currentNodes.filter((n: any) => n.isFileNode)
    if (fileNodesToRemove.length > 0) {
      nodesDataSet.remove(fileNodesToRemove.map(n => n.id))
    }
  }
  
  // ========== ZOOM FUNCTIONS ==========
  // Calculate the bounding box for a cluster's file nodes using known positions
  // File nodes are positioned with golden angle spiral around the cluster centroid
  const getClusterBoundingBox = (clusterId: number, centroidX: number, centroidY: number) => {
    const cluster = clusters.find(c => c.clusterId === clusterId)
    if (!cluster) return null
    
    const clusterFileCount = cluster.fileSet.size
    const maxClusterRadius = 150
    const orphanExtraRadius = 30
    
    // The outermost regular file node is at radius maxClusterRadius
    // Orphan nodes extend further by orphanExtraRadius
    const hasOrphans = orphanFiles.some(f => f.clusterId === clusterId)
    const maxRadius = hasOrphans ? maxClusterRadius + orphanExtraRadius : maxClusterRadius
    
    // Bounding box is the cluster centroid +/- maxRadius
    return {
      minX: centroidX - maxRadius,
      maxX: centroidX + maxRadius,
      minY: centroidY - maxRadius,
      maxY: centroidY + maxRadius,
    }
  }
  
  const zoomToCluster = (clusterId: number, centroidX: number, centroidY: number) => {
    if (!graphInstance.value) return
    
    const cluster = clusters.find(c => c.clusterId === clusterId)
    if (!cluster) return
    
    const clusterNodeId = `cluster-${clusterId}`
    
    // Calculate bounding box from known positions (no need to query vis-network)
    const bbox = getClusterBoundingBox(clusterId, centroidX, centroidY)
    if (!bbox) return
    
    graphInstance.value.fit({
      bounds: {
        from: clusterNodeId,
        x: [bbox.minX, bbox.maxX],
        y: [bbox.minY, bbox.maxY],
      },
      animation: { duration: 300, easingFunction: 'easeInOutQuad' },
    })
  }
  
  const zoomOut = () => {
    if (!graphInstance.value) return
    
    // Clear all file nodes
    clearAllFileNodes()
    
    // Reset drill-down state
    isDrillDown.value = false
    drilledClusterId.value = null
    
    // Zoom to fit all clusters
    graphInstance.value.fit({
      animation: { duration: 300, easingFunction: 'easeInOutQuad' },
    })
  }
  
  // Track current nodes for zoom calculation
  const currentNodes = ref<any[]>([])
  
  // ========== CLICK HANDLER: Select cluster only (no file nodes) ==========
  graphInstance.value?.on('click', async (params: any) => {
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      
      if (nodeId.startsWith('cluster-')) {
        const clusterId = parseInt(nodeId.replace('cluster-', ''))
        selectedCluster.value = clusters.find(c => c.clusterId === clusterId) ?? null
        
        // Clear drill-down state if active
        if (isDrillDown.value) {
          clearAllFileNodes()
          isDrillDown.value = false
          drilledClusterId.value = null
        }
      }
    } else {
      // Clicked background - deselect and clear everything
      selectedTag.value = null
      selectedFileDetail.value = null
      selectedCluster.value = null
      if (isDrillDown.value) {
        clearAllFileNodes()
        isDrillDown.value = false
        drilledClusterId.value = null
        zoomOut()
      }
    }
  })
  
  // ========== DOUBLE-CLICK HANDLER: Drill down into cluster ==========
  graphInstance.value.on('doubleClick', async (params: any) => {
    console.log('[DRILL-DOWN] doubleClick event fired', params)
    if (params.nodes.length > 0) {
      const nodeId = params.nodes[0]
      console.log('[DRILL-DOWN] clicked node:', nodeId)
      
      if (nodeId.startsWith('cluster-')) {
        const clusterId = parseInt(nodeId.replace('cluster-', ''))
        console.log('[DRILL-DOWN] clusterId:', clusterId)
        
        // Clear any existing file nodes from previous drill-down
        clearAllFileNodes()
        
        // Get cluster position — getPositions returns an object { nodeId: {x, y} }
        const positionMap = graphInstance.value?.getPositions([nodeId])
        console.log('[DRILL-DOWN] positionMap:', positionMap)
        const clusterPos = positionMap?.[nodeId]
        if (!clusterPos) {
          console.warn('[DRILL-DOWN] No position available for node:', nodeId)
          return
        }
        
        // Show file nodes for this cluster
        showFileNodesForCluster(clusterId, clusterPos.x, clusterPos.y)
        console.log('[DRILL-DOWN] showFileNodesForCluster called')
        
        // Update current nodes reference
        currentNodes.value = nodesDataSet.get()
        console.log('[DRILL-DOWN] currentNodes:', currentNodes.value.length)
        
        // Enter drill-down mode
        isDrillDown.value = true
        drilledClusterId.value = clusterId
        console.log('[DRILL-DOWN] isDrillDown:', isDrillDown.value, 'drilledClusterId:', drilledClusterId.value)
        
        // Select the cluster
        selectedCluster.value = clusters.find(c => c.clusterId === clusterId) ?? null
        
        // Zoom to fit the cluster and its files (uses calculated bounding box, no network query needed)
        zoomToCluster(clusterId, clusterPos.x, clusterPos.y)
        console.log('[DRILL-DOWN] zoomToCluster called')
      }
    }
  })
  
  // ========== HOVER HANDLER: Highlight cluster only ==========
  // Uses vis-network's highlightNodes API to avoid full re-renders that cause twitching
  graphInstance.value.on('hoverNode', (params: any) => {
    if (params.node) {
      const nodeId = params.node
      
      if (nodeId.startsWith('cluster-')) {
        const targetClusterId = parseInt(nodeId.replace('cluster-', ''))
        const targetNodeId = `cluster-${targetClusterId}`
        
        // Get connected cluster nodes using vis-network's built-in method
        const connectedNodes = graphInstance.value?.getConnectedNodes(targetNodeId) || []
        const highlightSet = new Set([targetNodeId, ...connectedNodes])
        
        // Use highlightNodes API — this is a GPU-accelerated highlight that doesn't trigger re-renders
        graphInstance.value?.highlightNodes(Array.from(highlightSet))
      }
    }
  })
  
  graphInstance.value.on('blurNode', () => {
    // Clear highlight using vis-network's API — no re-render needed
    graphInstance.value?.highlightNodes([])
  })
}

function renderTagNetwork(Network: any, DataSet: any) {
  const { tags, edges } = graphData.value
  
  // Reset positions for fresh layout
  for (let i = 0; i < tags.length; i++) {
    delete tags[i].x
    delete tags[i].y
  }

  const nodes = new DataSet(
    tags.map((tag: GraphTag) => ({
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
  const filteredEdges = edges
    .filter((edge: GraphEdge) => edge.shared_files >= 1)
    .sort((a: GraphEdge, b: GraphEdge) => b.shared_files - a.shared_files)
    .slice(0, 500)
  
  const edgesDataSet = new DataSet(
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
  
  networkDataSet.value = { nodes: nodes, edges: edgesDataSet }
  
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
}

function buildFileTooltip(file: ClusterFileNode, clusters: TagCluster[]): string {
  const cluster = clusters.find(c => c.clusterId === file.clusterId)
  const tagsHtml = file.tags.map(t => t.name).join(', ')
  return `<strong>${file.file_name}</strong><br>Tags: ${tagsHtml}${cluster ? `<br>Cluster: ${cluster.name}` : ''}`
}

function buildClusterTooltip(cluster: TagCluster): string {
  const tagsHtml = cluster.dominantTags.map(t => t.name).join(', ')
  return `<strong>${cluster.name}</strong><br>${cluster.fileCount} files<br>Dominant tags: ${tagsHtml}`
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
    const files = result.files || []
    // Transform files to include 16x16 preview URLs via the local proxy
    listTagFiles.value = files.map((file: { file_id: string; file_name: string; has_description: boolean }) => ({
      ...file,
      preview_url: `/api/files/preview-proxy/${file.file_id}?x=16&y=16`,
    }))
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
  // Set the correct state variable for the modal (FIX: was setting selectedFileDetail but modal checks selectedDescFileDetail)
  selectedDescFileDetail.value = selectedFileDetail.value
}

// ========== Image Enlargement ==========
function openEnlargedPreview(fileId: string, fileName: string) {
  openPreview({
    fileId: Number(fileId.replace(/\D/g, '')) || 0,
    filename: fileName,
    previewUrl: `/api/files/preview-proxy/${fileId}?x=1080&y=1080`,
  })
}

// ========== Pin Toggle ==========
async function togglePin(descriptionId: number, currentPinned: boolean) {
  try {
    const result = await $fetch('/api/settings/rag-index/description-pin', {
      method: 'PUT',
      body: { descriptionId, pinned: !currentPinned },
    })
    
    // Update the description in place in the modal
    if (selectedDescFileDetail.value) {
      const desc = selectedDescFileDetail.value.descriptions.find((d: any) => d.id === descriptionId)
      if (desc) {
        desc.pinned = !currentPinned
      }
    }
    
    // Also update in the descriptions grid
    const descEntry = descriptions.value.find(d => d.descriptions.some((d2: any) => d2.id === descriptionId))
    if (descEntry) {
      const desc = descEntry.descriptions.find((d2: any) => d2.id === descriptionId)
      if (desc) {
        desc.pinned = !currentPinned
      }
    }
  } catch (error: any) {
    console.error('Failed to toggle pin:', error)
    alert(`Failed to toggle pin: ${error.message || 'Unknown error'}`)
  }
}

// ========== Custom Description Creation ==========
async function createCustomDescription() {
  if (!selectedDescFileDetail.value || !newCustomDescription.value.trim()) return
  if (newCustomDescription.value.trim().length < 10) {
    alert('Description must be at least 10 characters long')
    return
  }
  
  isCreatingDescription.value = true
  try {
    const result = await $fetch('/api/settings/rag-index/description-create', {
      method: 'POST',
      body: {
        file_id: selectedDescFileDetail.value.file_id,
        description: newCustomDescription.value.trim(),
      },
    })
    
    // Add the new description to the modal
    if (selectedDescFileDetail.value) {
      selectedDescFileDetail.value.descriptions.push({
        id: result.description.id,
        description: result.description.description,
        pinned: result.description.pinned,
        createdAt: new Date().toISOString(),
      })
    }
    
    // Add/update in the descriptions grid
    const descEntry = descriptions.value.find(d => d.file_id === selectedDescFileDetail.value.file_id)
    if (descEntry) {
      descEntry.descriptions.push({
        id: result.description.id,
        description: result.description.description,
        pinned: result.description.pinned,
        createdAt: new Date().toISOString(),
      })
    }
    
    // Reset input
    newCustomDescription.value = ''
    showCustomDescriptionInput.value = false
  } catch (error: any) {
    console.error('Failed to create description:', error)
    alert(`Failed to create description: ${error.message || 'Unknown error'}`)
  } finally {
    isCreatingDescription.value = false
  }
}

function cancelCustomDescription() {
  newCustomDescription.value = ''
  showCustomDescriptionInput.value = false
}

// ========== DRILL-DOWN ZOOM OUT (global handler) ==========
function zoomOutFromDrillDown() {
  if (!graphInstance.value) return
  
  // Get the network's data set to clear file nodes
  const data = graphInstance.value.getData()
  if (data.nodes) {
    const allNodes = data.nodes.get()
    const fileNodesToRemove = allNodes.filter((n: any) => n.isFileNode)
    if (fileNodesToRemove.length > 0) {
      graphInstance.value.remove(fileNodesToRemove.map((n: any) => n.id))
    }
  }
  
  // Reset drill-down state
  isDrillDown.value = false
  drilledClusterId.value = null
  
  // Zoom to fit all clusters
  graphInstance.value.fit({
    animation: { duration: 300, easingFunction: 'easeInOutQuad' },
  })
}

// ========== Lifecycle ==========
onMounted(() => {
  fetchGraphData()
  
  // Escape key handler to zoom out from drill-down
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && isDrillDown.value) {
      zoomOutFromDrillDown()
    }
  }
  window.addEventListener('keydown', handleKeyDown)
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
          <div class="flex-1 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden relative">
            <!-- View Mode Toggle -->
            <div class="absolute top-3 left-3 z-10 flex bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
              <button
                @click="graphViewMode = 'clusters'"
                :class="graphViewMode === 'clusters'
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'"
                class="px-3 py-1.5 text-xs font-medium flex items-center gap-1.5"
              >
                <Filter class="w-3.5 h-3.5" />
                Clusters
              </button>
              <button
                @click="graphViewMode = 'tags'"
                :class="graphViewMode === 'tags'
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'"
                class="px-3 py-1.5 text-xs font-medium flex items-center gap-1.5 border-l border-gray-200 dark:border-gray-700"
              >
                <Tag class="w-3.5 h-3.5" />
                Tags
              </button>
            </div>
            
            <!-- Cluster Legend -->
            <div v-if="graphViewMode === 'clusters' && clusterGraphData?.clusters" class="absolute top-3 right-3 z-10 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-3 max-h-[calc(100vh-420px)] overflow-y-auto" style="max-width: 200px;">
              <p class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Clusters</p>
              <div class="space-y-1">
                <button
                  v-for="cluster in clusterGraphData.clusters.slice(0, 10)"
                  :key="cluster.clusterId"
                  @click="selectedCluster = cluster"
                  :class="selectedCluster?.clusterId === cluster.clusterId
                    ? 'bg-gray-100 dark:bg-gray-700'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700'"
                  class="w-full flex items-center gap-2 px-2 py-1 rounded text-left"
                >
                  <span class="w-3 h-3 rounded-full flex-shrink-0" :style="{ backgroundColor: cluster.color }"></span>
                  <span class="text-xs text-gray-700 dark:text-gray-300 truncate">{{ cluster.name }}</span>
                  <span class="text-xs text-gray-400 ml-auto">{{ cluster.fileCount }}</span>
                </button>
              </div>
            </div>
            
            <div ref="graphContainer" class="w-full h-full"></div>
          </div>
          
          <!-- Detail Panel -->
          <div class="w-96 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-y-auto">
            <!-- Cluster Selected State -->
            <div v-if="selectedCluster && graphViewMode === 'clusters'" class="p-4">
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                  <span class="w-4 h-4 rounded-full" :style="{ backgroundColor: selectedCluster.color }"></span>
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ selectedCluster.name }}</h3>
                  <span v-if="isDrillDown" class="text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400 rounded-full">
                    Drill-down
                  </span>
                </div>
                <button @click="selectedCluster = null" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                  <X class="w-4 h-4" />
                </button>
              </div>
              <div class="grid grid-cols-2 gap-2 text-sm mb-4">
                <div class="text-gray-500 dark:text-gray-400">Files:</div>
                <div class="text-gray-900 dark:text-gray-100">{{ selectedCluster.fileCount }}</div>
                <div class="text-gray-500 dark:text-gray-400">Dominant Tags:</div>
                <div class="text-gray-900 dark:text-gray-100 text-xs">
                  {{ selectedCluster.dominantTags.map(t => t.name).join(', ') }}
                </div>
              </div>
              
              <!-- Cluster files button -->
              <button
                @click="expandedListTag = selectedCluster.clusterId"
                class="w-full px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center justify-center gap-2"
              >
                <ImageIcon class="w-4 h-4" />
                View Files
              </button>
            </div>
            
            <!-- Tag Selected State (for tag view mode) -->
            <div v-else-if="selectedTag" class="p-4">
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
                    class="w-full h-40 object-cover cursor-pointer"
                    @click="openEnlargedPreview(selectedFileDetail.file_id, selectedFileDetail.file_name)"
                    @error="(e: any) => e.target.style.display='none'"
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
                      class="p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300 flex items-start gap-1"
                    >
                      <button
                        @click.stop="togglePin(desc.id, desc.pinned)"
                        class="flex-shrink-0 mt-0.5 hover:scale-110 transition-transform"
                        :title="desc.pinned ? 'Unpin' : 'Pin'"
                      >
                        <Pin v-if="desc.pinned" class="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
                        <PinOff v-else class="w-3.5 h-3.5 text-gray-400" />
                      </button>
                      <span v-if="desc.pinned" class="text-xs text-yellow-600 dark:text-yellow-400">(pinned)</span>
                      <span class="flex-1">{{ desc.description }}</span>
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
              <template v-for="tag in listTags" :key="tag.id">
                <tr
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
                  <td class="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{{ tag.files_with_descriptions }} files</td>
                  <td class="px-4 py-3"><span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">Regular</span></td>
                </tr>
                <!-- Expanded Tag Files Row - rendered inside v-for, directly after the selected tag -->
                <tr v-if="expandedListTag === tag.id" class="bg-blue-50/50 dark:bg-blue-900/5">
                  <td :colspan="5" class="px-4 py-0">
                    <div class="p-3">
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
                          <div class="w-4 h-4 flex-shrink-0 flex items-center justify-center">
                            <img
                              v-if="file.preview_url"
                              :src="file.preview_url"
                              :alt="file.file_name"
                              class="w-4 h-4 rounded object-cover"
                              @error="(e) => (e.currentTarget.style.display = 'none')"
                            />
                            <ImageIcon v-show="!file.preview_url" class="w-4 h-4 text-gray-400" />
                          </div>
                          <span class="text-gray-700 dark:text-gray-300">{{ file.file_name }}</span>
                          <FileText v-if="file.has_description" class="w-3 h-3 text-green-500" />
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
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
            <!-- Thumbnail with Enlarge Button -->
            <div class="h-32 bg-gray-200 dark:bg-gray-600 overflow-hidden relative group">
              <img
                :src="desc.preview_url"
                :alt="desc.file_name"
                class="w-full h-full object-cover"
                @error="(e: any) => e.target.style.display='none'"
              />
              <!-- Enlarge Button (Zoom) -->
              <button
                @click.stop="openEnlargedPreview(desc.file_id, desc.file_name)"
                class="absolute top-2 right-2 p-1.5 rounded-md bg-black/50 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/70"
                title="View enlarged"
              >
                <ZoomIn class="w-3.5 h-3.5" />
              </button>
            </div>
            <!-- Content -->
            <div class="p-3">
              <p class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate mb-2">{{ desc.file_name }}</p>
              <!-- All descriptions for this file with Pin buttons -->
              <div class="space-y-1">
                <div
                  v-for="d in desc.descriptions"
                  :key="d.id"
                  class="text-xs text-gray-500 dark:text-gray-400 flex items-start gap-1"
                >
                  <button
                    @click.stop="togglePin(d.id, d.pinned)"
                    class="flex-shrink-0 mt-0.5 hover:scale-110 transition-transform"
                    :title="d.pinned ? 'Unpin' : 'Pin'"
                  >
                    <Pin v-if="d.pinned" class="w-3 h-3 text-yellow-500 fill-yellow-500" />
                    <PinOff v-else class="w-3 h-3 text-gray-400" />
                  </button>
                  <span v-if="d.pinned" class="text-yellow-600 dark:text-yellow-400 font-medium mr-1">📌</span>
                  <span class="line-clamp-3 flex-1">{{ d.description }}</span>
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
        <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
          <div class="p-6">
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ selectedDescFileDetail.file_name }}</h3>
              <button
                @click="selectedDescFileDetail = null"
                class="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X class="w-5 h-5" />
              </button>
            </div>
            
            <!-- Image Preview with Enlarge Button -->
            <div class="mb-4 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-700 relative group">
              <img
                :src="selectedDescFileDetail.preview_url"
                :alt="selectedDescFileDetail.file_name"
                class="w-full h-80 object-cover"
                @error="(e: any) => e.target.style.display='none'"
              />
              <!-- Enlarge Button Overlay -->
              <button
                @click="openEnlargedPreview(selectedDescFileDetail.file_id, selectedDescFileDetail.file_name)"
                class="absolute bottom-3 right-3 p-2 rounded-md bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80 flex items-center gap-2"
                title="View enlarged"
              >
                <ZoomIn class="w-4 h-4" />
                <span class="text-sm">Enlarge</span>
              </button>
            </div>
          
            
            <!-- Descriptions with Pin Toggle -->
            <div v-if="selectedDescFileDetail.descriptions.length > 0" class="mb-4">
              <p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Descriptions:</p>
              <div class="space-y-2">
                <div
                  v-for="desc in selectedDescFileDetail.descriptions"
                  :key="desc.id"
                  class="p-3 bg-gray-50 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300 flex items-start gap-2"
                >
                  <button
                    @click.stop="togglePin(desc.id, desc.pinned)"
                    class="flex-shrink-0 mt-0.5 hover:scale-110 transition-transform"
                    :title="desc.pinned ? 'Unpin' : 'Pin'"
                  >
                    <Pin v-if="desc.pinned" class="w-4 h-4 text-yellow-500 fill-yellow-500" />
                    <PinOff v-else class="w-4 h-4 text-gray-400" />
                  </button>
                  <div class="flex-1">
                    <span v-if="desc.pinned" class="inline-block px-1.5 py-0.5 text-xs font-medium text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30 rounded mr-2">📌 PINNED</span>
                    <p>{{ desc.description }}</p>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Write Custom Description Input -->
            <div class="border-t border-gray-200 dark:border-gray-700 pt-4">
              <button
                v-if="!showCustomDescriptionInput"
                @click="showCustomDescriptionInput = true"
                class="px-4 py-2 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 flex items-center gap-2"
              >
                <Plus class="w-4 h-4" />
                Write Custom Description
              </button>
              
              <div v-else class="space-y-3">
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Custom Description:</label>
                  <textarea
                    v-model="newCustomDescription"
                    rows="4"
                    placeholder="Write your description here (min. 10 characters)..."
                    class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  ></textarea>
                </div>
                <div class="flex items-center gap-2">
                  <button
                    @click="createCustomDescription"
                    :disabled="isCreatingDescription || !newCustomDescription.trim()"
                    class="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Send v-if="!isCreatingDescription" class="w-4 h-4" />
                    <Loader2 v-else class="w-4 h-4 animate-spin" />
                    {{ isCreatingDescription ? 'Creating...' : 'Create Description' }}
                  </button>
                  <button
                    @click="cancelCustomDescription"
                    class="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 flex items-center gap-2"
                  >
                    <X class="w-4 h-4" />
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Image Preview Modal (Enlarged View) -->
    <ImagePreviewModal :state="previewState" :close="closePreview" :navigate="navigatePreview" />
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
