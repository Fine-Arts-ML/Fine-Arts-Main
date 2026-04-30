import { db } from '~/lib/db'
import { shops, shopAccountMatrix, accounts } from '~/lib/schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
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

    // Check if shop exists
    const existingShop = await db.select({ shopId: shops.shopId }).from(shops).where(eq(shops.shopId, shopId))
    if (!existingShop.length) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Shop not found',
      })
    }

    // Fetch accounts linked to this shop
    const result = await db
      .select({
        accountId: shopAccountMatrix.accountId,
        accountName: accounts.accountName,
      })
      .from(shopAccountMatrix)
      .innerJoin(accounts, eq(shopAccountMatrix.accountId, accounts.accountId))
      .where(eq(shopAccountMatrix.shopId, BigInt(shopId)))

    return result.map(row => ({
      account_id: typeof row.accountId === 'string' ? parseInt(row.accountId, 10) : Number(row.accountId),
      account_name: row.accountName,
    }))
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch shop accounts',
      data: error.message,
    })
  }
})
