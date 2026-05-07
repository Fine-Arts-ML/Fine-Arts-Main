import { db } from '~/lib/db'
import { shopAccountMatrix } from '~/lib/schema'

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

    await db.insert(shopAccountMatrix).values({
      shopId: BigInt(id),
      accountId: BigInt(accountId),
    })

    return { success: true }
  } catch (error: any) {
    if (error.statusCode) throw error
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to link shop and account',
      data: error.message,
    })
  }
})