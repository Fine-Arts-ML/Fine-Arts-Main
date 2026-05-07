import { db } from '~/lib/db'
import { shops, shopAccountMatrix } from '~/lib/schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Shop ID is required',
    })
  }

  const shopId = parseInt(id, 10)
  if (isNaN(shopId)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid shop ID',
    })
  }

  try {
    // First, unlink all accounts from this shop
    await db.delete(shopAccountMatrix).where(
      eq(shopAccountMatrix.shopId as any, BigInt(shopId))
    )

    // Then delete the shop
    await db.delete(shops).where(eq(shops.shopId, shopId))

    return { success: true, shopId }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to delete shop'
    throw createError({
      statusCode: 500,
      statusMessage: message,
    })
  }
})