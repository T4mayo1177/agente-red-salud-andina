# Etapa 1: compilar el frontend con la URL del backend.
# VITE_API_URL queda dentro del JavaScript público: nunca pase claves por aquí.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Etapa 2: servir los archivos estáticos con nginx en el puerto 8080 (el de Cloud Run).
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
