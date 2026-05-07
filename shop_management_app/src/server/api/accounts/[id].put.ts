import { db } from '~/lib/db'
import { accounts } from '~/lib/schema'
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
    const body = await readBody(event)
    const { accountName } = body

    if (!accountName || typeof accountName !== 'string' || accountName.trim().length === 0) {
      throw createError({
        statusCode: 400,
        statusMessage: 'Account name is required',
      })
    }

    // Check if account exists
    const existingAccount = await db
      .select()
      .from(accounts)
      .where(eq(accounts.accountId, accountId))
      .limit(1)

    if (existingAccount.length === 0) {
      throw createError({
        statusCode: 404,
        statusMessage: 'Account not found',
      })
    }

    // Update the account name
    const result = await db
      .update(accounts)
      .set({ accountName: accountName.trim() })
      .where(eq(accounts.accountId, accountId))
      .returning()

    return {
      account_id: result[0].accountId,
      account_name: result[0].accountName,
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[update-account] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to update account',
      data: error.message,
    })
  }
})
