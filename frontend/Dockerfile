# frontend/Dockerfile
FROM node:24-alpine AS builder

WORKDIR /app

# Install dependencies first (cached layer)
COPY frontend/package*.json ./
RUN npm ci

# Application code
COPY frontend/ ./

# Build
RUN npm run build

# Production image
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]