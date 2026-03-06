#!/bin/sh
set -e
export PGPASSWORD="${POSTGRES_PASSWORD}"
echo "[scheduler-entrypoint] Waiting for PostgreSQL..."
until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  sleep 2
done
echo "[scheduler-entrypoint] DB ready, starting scheduler..."
exec python scheduler_runner.py
