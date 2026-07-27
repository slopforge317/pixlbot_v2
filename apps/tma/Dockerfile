# syntax=docker/dockerfile:1

FROM node:24.18.0-alpine AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_API_URL=/api
ARG VITE_MOCK_INIT_DATA=
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_MOCK_INIT_DATA=$VITE_MOCK_INIT_DATA

RUN pnpm run build

FROM nginx:stable-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
