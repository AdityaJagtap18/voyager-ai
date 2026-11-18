# Voyager-AI — React frontend (Vite build → nginx static serve)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_BASE_URL is baked in at build time — passed via --build-arg
ARG VITE_API_BASE_URL=https://voyager-ai-api.adityajagtap.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- Production image ----
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing: 404 → index.html so React Router handles all paths
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
