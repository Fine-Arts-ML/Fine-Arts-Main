import { db } from '~/lib/db'
import { accounts } from '~/lib/schema'
import { max } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  try {
    const body = await readBody(event)
    const { accountName } = body

    console.log('[create-account] Received request, body:', JSON.stringify(body))

    if (!accountName || typeof accountName !== 'string' || accountName.trim().length === 0) {
      console.log('[create-account] Validation failed: invalid accountName')
      throw createError({
        statusCode: 400,
        statusMessage: 'Account name is required',
      })
    }

    // Get the next available ID by finding max account_id and adding 1
    const maxResult = await db.select({ max: max(accounts.accountId) }).from(accounts)
    const nextId = (maxResult[0]?.max ?? 0) + 1
    console.log(`[create-account] Max account_id: ${maxResult[0]?.max}, nextId: ${nextId}`)

    // Insert with explicit ID
    const result = await db
      .insert(accounts)
      .values({ accountId: nextId, accountName: accountName.trim() })
      .returning()

    console.log(`[create-account] Successfully created account:`, result[0])

    return {
      account_id: result[0].accountId,
      account_name: result[0].accountName,
    }
  } catch (error: any) {
    if (error.statusCode) throw error
    console.error('[create-account] Error:', error)
    throw createError({
      statusCode: 500,
      statusMessage: 'Failed to create account',
      data: error.message,
    })
  }
})