FROM node:20-slim AS build

WORKDIR /app

ARG VITE_API_BASE
ARG VITE_SENTRY_DSN
ENV VITE_API_BASE=${VITE_API_BASE}
ENV VITE_SENTRY_DSN=${VITE_SENTRY_DSN}

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080
