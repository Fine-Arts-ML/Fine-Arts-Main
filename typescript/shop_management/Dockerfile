# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files for dependency installation
COPY package.json package-lock.json ./

# Install dependencies (with postinstall script for nuxt prepare)
RUN npm ci 2>&1

# Copy source code
COPY . .

# Build application
RUN npm run build 2>&1

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nuxtjs

# Copy built application from build stage
COPY --from=build --chown=nuxtjs:nodejs /app/.output ./.output

# Install curl for healthchecks
RUN apk add --no-cache curl

USER nuxtjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", ".output/server/index.mjs"]
