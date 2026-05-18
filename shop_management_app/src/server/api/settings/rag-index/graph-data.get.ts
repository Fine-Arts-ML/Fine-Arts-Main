/**
 * Graph Data API
 * Returns all data needed to render the tag knowledge graph:
 * - Tags with file counts and description info
 * - Tag co-occurrence edges (tags that share files)
 * - Tag-to-file mappings for the detail panel
 */

import { Pool } from 'pg'

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

export default defineEventHandler(async (event) => {
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
    // 1. Get all tags with file counts and description counts
    const tagsQuery = `
      SELECT
        s.id,
        s.name,
        COUNT(DISTINCT m.objectid::text)::int AS num_files,
        COUNT(DISTINCT CASE WHEN d.file_id IS NOT NULL THEN m.objectid::text END)::int AS files_with_descriptions
      FROM oc_systemtag s
      LEFT JOIN oc_systemtag_object_mapping m ON s.id = m.systemtagid
      LEFT JOIN bre_descriptions d ON m.objectid::text = d.file_id
      GROUP BY s.id, s.name
      HAVING COUNT(DISTINCT m.objectid::text) >= 1
      ORDER BY num_files DESC
    `
    const tagsResult = await pool.query(tagsQuery)
    const tags: GraphTag[] = tagsResult.rows.map(row => ({
      id: parseInt(row.id),
      name: row.name,
      num_files: parseInt(row.num_files),
      files_with_descriptions: parseInt(row.files_with_descriptions),
    }))

    // 2. Get tag co-occurrence edges
    const edgesQuery = `
      SELECT 
        m1.systemtagid AS tag_id_1,
        m2.systemtagid AS tag_id_2,
        COUNT(DISTINCT m1.objectid)::int AS shared_files
      FROM oc_systemtag_object_mapping m1
      JOIN oc_systemtag_object_mapping m2 ON m1.objectid = m2.objectid 
        AND m1.systemtagid < m2.systemtagid
      GROUP BY m1.systemtagid, m2.systemtagid
      HAVING COUNT(DISTINCT m1.objectid) >= 1
      ORDER BY shared_files DESC
    `
    const edgesResult = await pool.query(edgesQuery)
    const edges: GraphEdge[] = edgesResult.rows.map(row => ({
      tag_id_1: parseInt(row.tag_id_1),
      tag_id_2: parseInt(row.tag_id_2),
      shared_files: parseInt(row.shared_files),
    }))

    // 3. Get tag-to-file mappings (for all tags, used by detail panel)
    const mappingsQuery = `
      SELECT 
        s.id AS tag_id,
        m.objectid::text AS file_id,
        fc.name AS file_name,
        CASE WHEN d.file_id IS NOT NULL THEN true ELSE false END AS has_description
      FROM oc_systemtag s
      JOIN oc_systemtag_object_mapping m ON s.id = m.systemtagid
      LEFT JOIN oc_filecache fc ON m.objectid::text = fc.fileid::text
        AND fc.name NOT LIKE '.%' AND fc.mimetype IN (
          SELECT id FROM oc_mimetypes WHERE mimetype LIKE 'image/%'
        )
      LEFT JOIN bre_descriptions d ON m.objectid::text = d.file_id
      WHERE m.objectid::text IN (
        SELECT DISTINCT objectid::text FROM oc_systemtag_object_mapping
      )
      ORDER BY s.id, fc.name
    `
    const mappingsResult = await pool.query(mappingsQuery)
    
    // Group mappings by tag_id
    const tagFileMappings: Record<number, TagFileMapping[]> = {}
    for (const row of mappingsResult.rows) {
      const tagId = parseInt(row.tag_id)
      if (!tagFileMappings[tagId]) {
        tagFileMappings[tagId] = []
      }
      tagFileMappings[tagId].push({
        file_id: row.file_id,
        file_name: row.file_name || 'Unknown',
        has_description: row.has_description,
      })
    }

    // 4. Get global stats (server-computed to avoid frontend counting bugs)
    const statsQuery = `
      SELECT
        (SELECT COUNT(DISTINCT objectid::text)::int FROM oc_systemtag_object_mapping) AS totalFilesWithTags,
        (SELECT COUNT(DISTINCT d.file_id)::int
         FROM bre_descriptions d
         INNER JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text) AS totalFilesWithDescriptions,
        (SELECT COUNT(DISTINCT d.id)::int
         FROM bre_descriptions d
         INNER JOIN oc_systemtag_object_mapping m ON d.file_id = m.objectid::text) AS totalDescriptionMappings
    `
    const statsResult = await pool.query(statsQuery)
    const globalStats: GlobalStats = {
      totalFilesWithTags: parseInt(statsResult.rows[0].totalfileswithtags),
      totalFilesWithDescriptions: parseInt(statsResult.rows[0].totalfileswithdescriptions),
      totalDescriptionMappings: parseInt(statsResult.rows[0].totaldescriptionmappings),
    }

    return {
      tags,
      edges,
      tagFileMappings,
      globalStats,
    }
  } catch (error: any) {
    console.error('[graph-data] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: `Failed to fetch graph data: ${error.message}`,
    })
  } finally {
    await pool.end()
  }
})
