import { db } from '~/lib/db'
import { shops } from '~/lib/schema'
import { sql, max } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { shopName } = body

    if (!shopName || typeof shopName !== 'string' || shopName.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Shop name is required',
      })
    }

    // Get the next available ID by finding max shop_id and adding 1
    const maxResult = await db.select({ max: max(shops.shopId) }).from(shops)
    const nextId = (maxResult[0]?.max ?? 0) + 1

    // Insert with explicit ID
    const result = await db
      .insert(shops)
      .values({ shopId: nextId, shopName: shopName.trim() })
      .returning()

    return result[0]
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to create shop',
      data: error.message,
    })
  }
})