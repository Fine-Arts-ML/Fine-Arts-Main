// Database connection utility using PostgreSQL with Drizzle ORM
import { drizzle } from 'drizzle-orm/node-postgres'
import { Pool } from 'node_modules/@types/pg'
import * as schema from './schema'

let pool: Pool | null = null

export function getDb() {
  if (!pool) {
    const dbHost = process.env.DB_HOST || 'localhost'
    const dbPort = Number(process.env.DB_PORT) || 5432
    const dbName = process.env.DB_NAME || 'shop_management'
    const dbUser = process.env.DB_USER || 'postgres'
    const dbPassword = process.env.DB_PASSWORD || 'postgres'

    pool = new Pool({
      host: dbHost,
      port: dbPort,
      database: dbName,
      user: dbUser,
      password: dbPassword,
    })
  }
  return drizzle(pool, { schema })
}

export const db = getDb()
