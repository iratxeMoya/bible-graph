# Etapa dev: servidor de Vite con el código montado desde el host (docker compose).
FROM node:24-alpine AS dev
WORKDIR /app
USER node
EXPOSE 5173
CMD ["sh", "-c", "npm install && npm run dev"]

# Etapa build: genera el estático. Cloudflare Pages no usa este Dockerfile.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Etapa static: sirve el build con nginx para probarlo en local.
FROM nginx:alpine AS static
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
