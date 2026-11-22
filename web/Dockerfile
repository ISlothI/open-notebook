# syntax=docker/dockerfile:1
FROM node:26-trixie-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --ignore-scripts --no-audit --no-fund
COPY . .
# Vite keeps its cache next to the dependencies.
RUN mkdir -p node_modules/.vite node_modules/.vite-temp && chown -R 1000:1000 node_modules/.vite node_modules/.vite-temp
USER 1000:1000
CMD ["npm", "run", "dev"]

FROM dev AS builder
RUN npm run build -- --outDir /tmp/dist

FROM caddy:2-alpine@sha256:003a97808e781aa9f7e75cc2f43d34d461099031faf5e20faefb9f61126836f0 AS runtime
# The low-port capability is not needed, and it prevents starting without capabilities.
RUN setcap -r /usr/bin/caddy
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=builder /tmp/dist /srv
USER 65532:65532
EXPOSE 8080
