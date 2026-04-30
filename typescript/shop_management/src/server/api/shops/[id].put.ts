import { db } from '~/lib/db'
import { shops } from '~/lib/schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const body = await readBody(event)
    const { shopName } = body

    if (!id) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Shop ID is required',
      })
    }

    if (!shopName || typeof shopName !== 'string' || shopName.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Shop name is required',
      })
    }

    const shopId = parseInt(id, 10)
    if (isNaN(shopId)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid shop ID',
      })
    }

    // Check if shop exists
    const existingShop = await db.select({ shopName: shops.shopName }).from(shops).where(eq(shops.shopId, shopId))
    if (!existingShop.length) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Shop not found',
      })
    }

    // Update the shop
    const result = await db
      .update(shops)
      .set({ shopName: shopName.trim() })
      .where(eq(shops.shopId, shopId))
      .returning()

    if (!result.length) {
      throw createError({
        statusCode: 500,
        statusMessage: 'Failed to update shop',
      })
    }

    return {
      shop_id: result[0].shopId,
      shop_name: result[0].shopName,
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update shop',
      data: error.message,
    })
  }
})
