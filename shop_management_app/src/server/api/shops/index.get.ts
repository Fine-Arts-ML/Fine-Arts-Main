import { db } from '~/lib/db'
import { shops, shopAccountMatrix, fileJunction } from '~/lib/schema'
import { asc, count, countDistinct } from 'drizzle-orm'

export default defineEventHandler(async () => {
  try {
    // Fetch shops first
    const shopList = await db
      .select({
        shopId: shops.shopId,
        shopName: shops.shopName,
      })
      .from(shops)
      .orderBy(asc(shops.shopName))

    // Fetch account counts per shop
    const accountCounts = await db
      .select({
        shopId: shopAccountMatrix.shopId,
        accountCount: count(shopAccountMatrix.accountId),
      })
      .from(shopAccountMatrix)
      .groupBy(shopAccountMatrix.shopId)

    // Fetch file counts per shop from bre_file_junction (source of truth)
    // Use countDistinct to avoid double-counting files linked to multiple accounts
    const fileCounts = await db
      .select({
        shopId: fileJunction.shopId,
        fileCount: countDistinct(fileJunction.fileId),
      })
      .from(fileJunction)
      .groupBy(fileJunction.shopId)

    // Build lookup maps
    const accountCountMap = new Map<number, number>()
    for (const row of accountCounts) {
      accountCountMap.set(Number(row.shopId), Number(row.accountCount))
    }

    const fileCountMap = new Map<number, number>()
    for (const row of fileCounts) {
      fileCountMap.set(Number(row.shopId), Number(row.fileCount))
    }

    // Merge results
    return shopList.map(row => ({
      shop_id: Number(row.shopId),
      shop_name: row.shopName,
      account_count: accountCountMap.get(Number(row.shopId)) ?? 0,
      file_count: fileCountMap.get(Number(row.shopId)) ?? 0,
    }))
  } catch (error: any) {
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to fetch shops',
      data: error.message,
    })
  }
})
