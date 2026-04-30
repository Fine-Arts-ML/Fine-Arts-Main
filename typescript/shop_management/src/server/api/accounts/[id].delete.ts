import { db } from '~/lib/db'
import { accounts, shopAccountMatrix, accountIndex } from '~/lib/schema'
import { eq } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id')
  if (!id) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Account ID is required',
    })
  }

  const accountId = parseInt(id, 10)
  if (isNaN(accountId)) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid account ID',
    })
  }

  try {
    // First, remove all shop associations
    await db.delete(shopAccountMatrix).where(
      eq(shopAccountMatrix.accountId as any, BigInt(accountId))
    )

    // Remove all file associations
    await db.delete(accountIndex).where(eq(accountIndex.accountId, accountId))

    // Then delete the account
    await db.delete(accounts).where(eq(accounts.accountId, accountId))

    return { success: true, accountId }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Failed to delete account'
    throw createError({
      statusCode: 500,
      statusMessage: message,
    })
  }
})