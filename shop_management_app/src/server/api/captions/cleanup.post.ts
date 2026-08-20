// POST /api/captions/cleanup
// Removes orphaned captions that have no links in bre_gallery_image_captions

import { defineEventHandler } from 'h3'
import { db } from '~/lib/db'
import { sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const user = event.context.user
  if (!user) {
    throw createError({ statusCode: 401, statusMessage: 'Unauthorized' })
  }

  const result = await db.execute(sql`SELECT cleanup_orphaned_captions()`)
  return { deleted: Number(result.rows[0]?.cleanup_orphaned_captions ?? 0) }
})
