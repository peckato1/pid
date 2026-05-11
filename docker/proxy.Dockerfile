FROM docker.io/library/caddy:2-alpine

COPY docker/Caddyfile /etc/caddy/Caddyfile
COPY frontend /srv
