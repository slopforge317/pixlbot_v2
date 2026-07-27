# Этап 1: Сборка
FROM node:18-alpine as build
WORKDIR /app

# Копируем файлы зависимостей
COPY package*.json ./

# Устанавливаем зависимости
RUN npm ci --silent

# Копируем исходный код
COPY . .

# Собираем приложение
RUN npm run build

# ... (стадия build остается прежней) ...

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Порт 443 теперь основной
EXPOSE 80 443
CMD ["nginx", "-g", "daemon off;"]