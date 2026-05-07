import { db } from '~/lib/db'
import { displayName, displayNameMatrix } from '~/lib/schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const fileId = getRouterParam(event, 'fileId')

    if (!fileId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'File ID is required',
      })
    }

    // Fetch all display names (tags) associated with this file
    const result = await db
      .select({
        displayName: displayName.displayName,
      })
      .from(displayNameMatrix)
      .innerJoin(displayName, eq(displayNameMatrix.displayNameId, displayName.displayNameId))
      .where(eq(displayNameMatrix.fileId, fileId))

    return result.map(row => row.displayName)
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch tags',
      data: error.message,
    })
  }
})
