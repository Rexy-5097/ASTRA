# Multi-stage production Dockerfile for Next.js (ASTRA Platform)
# Optimized for Render, Railway, or standard VPS container deployments

# 1. Base stage: Install dependencies only when needed
FROM node:22-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy package management files
COPY package.json package-lock.json* ./
RUN npm ci

# 2. Builder stage: Rebuild the source code only when needed
FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables for production build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production

# Run the production build
RUN npm run build

# 3. Runner stage: Production image, copy all files and run Next.js
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy public static assets and built next directory
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Standard Next.js server start command (does not require output: 'standalone')
CMD ["npx", "next", "start"]
