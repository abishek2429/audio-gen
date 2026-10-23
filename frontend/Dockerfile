# ==============================================================================
# IncuBrix AI Background Music Engine — Frontend Production Container
# Multi-stage build: Node.js 20 builder -> Lightweight Nginx Alpine server
# ==============================================================================

# --- Stage 1: Build Static Assets ---
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source tree and compile bundle
COPY . .
RUN npm run build

# --- Stage 2: Serve with Nginx ---
FROM nginx:1.27-alpine

# Copy built static artifacts
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration with reverse proxy routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
