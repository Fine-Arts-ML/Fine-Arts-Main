import { db } from '~/lib/db'
import { advanceIndex, shopsIndex, shopAccountMatrix, accounts, accountIndex, displayName, displayNameMatrix } from '~/lib/schema'
import { eq, and, sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const query = getQuery(event).query as string | undefined
    const accountId = getQuery(event).accountId as string | undefined
    const limit = parseInt(getQuery(event).limit as string || '50', 10)
    const offset = parseInt(getQuery(event).offset as string || '0', 10)

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

    if (!query || query.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Search query is required',
      })
    }

    if (!accountId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Account ID is required',
      })
    }

    const accountNumId = parseInt(accountId, 10)
    if (isNaN(accountNumId)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid account ID',
      })
    }

    const searchQuery = `%${query.trim()}%`

    // Fetch files linked to this shop AND account, searching both filenames AND display names
    const result = await db
      .select({
        fileId: advanceIndex.fileId,
        filename: advanceIndex.name,
        previewUrl: advanceIndex.previewUrl,
        accountId: accountIndex.accountId,
        accountName: accounts.accountName,
      })
      .from(advanceIndex)
      .innerJoin(shopsIndex, sql`CAST(${advanceIndex.fileId} AS bigint) = ${shopsIndex.id}`)
      .innerJoin(accountIndex, sql`CAST(${advanceIndex.fileId} AS bigint) = ${accountIndex.fileId}`)
      .innerJoin(accounts, eq(accountIndex.accountId, accounts.accountId))
      .leftJoin(displayNameMatrix, sql`CAST(${advanceIndex.fileId} AS bigint) = ${displayNameMatrix.fileId}`)
      .leftJoin(displayName, eq(displayNameMatrix.displayNameId, displayName.displayNameId))
      .where(and(
        eq(shopsIndex.shopId, BigInt(shopId)),
        eq(accountIndex.accountId, BigInt(accountNumId)),
        or(
          sql`${advanceIndex.name} ILIKE ${searchQuery}`,
          sql`${displayName.displayName} ILIKE ${searchQuery}`
        )
      ))
      .limit(limit)
      .offset(offset)

    // Deduplicate by fileId
    const seen = new Set<number>()
    const uniqueResults = result.filter(row => {
      const fileId = Number(row.fileId)
      if (seen.has(fileId)) return false
      seen.add(fileId)
      return true
    })

    return uniqueResults
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to search files',
      data: error.message,
    })
  }
})
