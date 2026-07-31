# syntax=docker/dockerfile:1

FROM node:24.18.0-alpine AS build

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

RUN pnpm run build

FROM caddy:2.11.4-alpine

COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80 443

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
