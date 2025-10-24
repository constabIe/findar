FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --legacy-peer-deps

COPY . ./
RUN npm run build

FROM nginx:1.29.2-alpine

# Удалим дефолтный nginx html
RUN rm -rf /usr/share/nginx/html/*

# Копируем билд из предыдущего контейнера
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомный nginx.conf если нужно
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
