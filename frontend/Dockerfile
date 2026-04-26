FROM node:20-alpine AS build
WORKDIR /app

# Build-time only. Vite inlines this into the bundle when `npm run build` runs.
# Runtime `environment:` settings on the frontend service are ignored.
# Code reads `import.meta.env.VITE_API_BASE` (see `frontend/src/api.ts`).
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# SPA fallback + asset caching + /healthz
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q -O - http://127.0.0.1/healthz || exit 1
