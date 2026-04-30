# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Generate environment file
RUN echo "DB_HOST=${DB_HOST:-db}" > .env.local
RUN echo "DB_NAME=${DB_NAME:-shop_management}" >> .env.local
RUN echo "DB_USER=${DB_USER:-postgres}" >> .env.local
RUN echo "DB_PASSWORD=${DB_PASSWORD:-postgres}" >> .env.local
RUN echo "DB_PORT=${DB_PORT:-5432}" >> .env.local
RUN echo "NC_ACC=${NC_ACC:-}" >> .env.local
RUN echo "NC_PASS=${NC_PASS:-}" >> .env.local

# Build application
RUN npm run build

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nuxtjs

# Copy built application
COPY --from=build --chown=nuxtjs:nodejs /app/.output ./.output

USER nuxtjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server", "index.mjs"]
