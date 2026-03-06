#!/bin/sh
set -e
export PGPASSWORD="${POSTGRES_PASSWORD}"
echo "[entrypoint] Waiting for PostgreSQL..."
until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  sleep 2
done
echo "[entrypoint] DB ready, running migrations..."
./scripts/init_db.sh 2>/dev/null || true
./scripts/run_migration.sh 2>/dev/null || true
python scripts/init_ai_tables.py 2>/dev/null || true
echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 12135 --workers 4
