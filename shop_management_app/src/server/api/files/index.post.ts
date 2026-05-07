import { db } from '~/lib/db'
import { advanceIndex, shopsIndex } from '~/lib/schema'

export default defineEventHandler(async () => {
  try {
    const body = await readBody(event)
    const { name, previewUrl, shopId } = body

    if (!name || typeof name !== 'string' || name.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'File name is required',
      })
    }

    const result = await db
      .insert(advanceIndex)
      .values({
        name: name.trim(),
        previewUrl: previewUrl || null,
      })
      .returning()

    const file = result[0]

    // Also link to shop if provided
    if (shopId) {
      await db.insert(shopsIndex).values({
        id: String(file.fileId),
        shopId: Number(shopId),
      })
    }

    return file
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to create file',
      data: error.message,
    })
  }
})