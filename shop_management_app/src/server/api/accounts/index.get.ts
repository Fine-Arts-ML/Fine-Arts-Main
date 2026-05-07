import { db } from '~/lib/db'
import { accounts, shopAccountMatrix, shops } from '~/lib/schema'
import { eq, asc, count } from 'drizzle-orm'

export default defineEventHandler(async () => {
  try {
    const result = await db
      .select({
        accountId: accounts.accountId,
        accountName: accounts.accountName,
        shopCount: count(shops.shopId),
      })
      .from(accounts)
      .leftJoin(shopAccountMatrix, eq(accounts.accountId, shopAccountMatrix.accountId))
      .leftJoin(shops, eq(shopAccountMatrix.shopId, shops.shopId))
      .groupBy(accounts.accountId, accounts.accountName)
      .orderBy(asc(accounts.accountName))

    return result.map(row => ({
      account_id: Number(row.accountId),
      account_name: row.accountName,
      shop_count: row.shopCount,
    }))
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch accounts',
      data: error.message,
    })
  }
})