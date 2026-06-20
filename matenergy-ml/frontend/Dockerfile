# ============================================================
# MatEnergy-ML — Frontend Dockerfile
# Multi-stage: build with Node 20-alpine, serve with nginx:alpine
# Non-root user in production stage
# ============================================================

# ---- Stage 1: Build ----
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package.json package-lock.json* ./
RUN npm install

# Copy source and build
COPY . .
RUN npm run build

# ---- Stage 2: Serve ----
FROM nginx:alpine AS production

# Create non-root user for nginx
RUN addgroup -g 1001 -S nginxgroup \
 && adduser  -u 1001 -S nginxuser -G nginxgroup

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config to support React Router (SPA fallback)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Fix permissions so nginx can run as non-root
RUN chown -R nginxuser:nginxgroup /usr/share/nginx/html \
 && chown -R nginxuser:nginxgroup /var/cache/nginx \
 && chown -R nginxuser:nginxgroup /var/log/nginx \
 && touch /var/run/nginx.pid \
 && chown nginxuser:nginxgroup /var/run/nginx.pid

USER nginxuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
