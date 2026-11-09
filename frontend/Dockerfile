FROM node:22-alpine AS build

ARG VITE_API_BASE_URL=
ARG VITE_API_DOCS_URL=/docs
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_DOCS_URL=${VITE_API_DOCS_URL}

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
