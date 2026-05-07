import { db } from '~/lib/db'
import { accounts, shopAccountMatrix, accountIndex, fileJunction, displayNameMatrix } from '~/lib/schema'
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
    // Step 1: Remove all file junction records (shop + file + account relationships with published status)
    await db.delete(fileJunction).where(
      eq(fileJunction.accountId, accountId)
    )

    // Step 2: Remove display name mappings for this account
    await db.delete(displayNameMatrix).where(
      eq(displayNameMatrix.accountId, accountId)
    )

    // Step 3: Remove all shop associations
    await db.delete(shopAccountMatrix).where(
      eq(shopAccountMatrix.accountId as any, BigInt(accountId))
    )

    // Step 4: Remove all account-file index associations
    await db.delete(accountIndex).where(eq(accountIndex.accountId, accountId))

    // Step 5: Finally delete the account itself
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