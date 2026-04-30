import { db } from '~/lib/db'
import { shopAccountMatrix } from '~/lib/schema'
import { eq, and } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const id = getRouterParam(event, 'id')
    const body = await readBody(event)
    const { accountId } = body

    if (!id || !accountId) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Shop ID and Account ID are required',
      })
    }

    const shopId = parseInt(id, 10)
    if (isNaN(shopId)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid shop ID',
      })
    }

    const accountNumId = typeof accountId === 'string' ? parseInt(accountId, 10) : Number(accountId)
    if (isNaN(accountNumId)) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Invalid account ID',
      })
    }

    // Delete the link from the matrix
    await db
      .delete(shopAccountMatrix)
      .where(and(eq(shopAccountMatrix.shopId, BigInt(shopId)), eq(shopAccountMatrix.accountId, BigInt(accountNumId))))

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to unlink shop and account',
      data: error.message,
    })
  }
})
