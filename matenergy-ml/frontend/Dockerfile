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

# Custom nginx config template — the base nginx:alpine image's inherited
# entrypoint runs envsubst on *.template files in /etc/nginx/templates/ at
# container start, writing the result to /etc/nginx/conf.d/. This lets
# PORT/BACKEND_HOST/BACKEND_PORT be overridden per-environment (e.g. a cloud
# platform's private networking hostname) without rebuilding the image.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Defaults match the docker-compose service name/ports — unchanged local
# behavior. Override BACKEND_HOST (and PORT, on platforms that assign one)
# when deploying somewhere without a "backend" DNS alias.
ENV PORT=80
ENV BACKEND_HOST=backend
ENV BACKEND_PORT=8000

# Fix permissions so nginx can run as non-root
RUN chown -R nginxuser:nginxgroup /usr/share/nginx/html \
 && chown -R nginxuser:nginxgroup /var/cache/nginx \
 && chown -R nginxuser:nginxgroup /var/log/nginx \
 && chown -R nginxuser:nginxgroup /etc/nginx/conf.d \
 && chown -R nginxuser:nginxgroup /etc/nginx/templates \
 && touch /var/run/nginx.pid \
 && chown nginxuser:nginxgroup /var/run/nginx.pid

USER nginxuser

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
