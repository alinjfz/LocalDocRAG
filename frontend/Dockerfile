# ── DocMind Frontend Dockerfile ───────────────────────────────────────────────
# Multi-arch (linux/amd64 + linux/arm64) — runs on Raspberry Pi 4/5
# Multi-stage: build with Node, serve with nginx (lightweight production image)

# ── Stage 1: Build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (separate layer for better caching)
COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile 2>/dev/null || npm install

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Serve ────────────────────────────────────────────────────────────
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config for SPA (all routes → index.html)
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
