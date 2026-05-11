#!/bin/bash
set -euo pipefail

# Dump container env so cron jobs (which run with an empty env) can source it.
umask 077
{
  while IFS='=' read -r k v; do
    printf 'export %s=%q\n' "$k" "$v"
  done < <(env)
} > /etc/container_env

# Catch-up: if no sync has been recorded today, run one now. The script is a
# no-op when gtfs_feed_info already has a row dated today.
cd /app
python pid_gtfs_sync.py --download --if-stale --archive-dir /gtfs_archives \
    || echo "startup catch-up sync failed; continuing into cron loop"

exec cron -f
