#!/bin/sh
set -eu

postgres_ready() {
  .venv/bin/python - <<'PY'
import os
import sys

import psycopg

database_url = os.environ.get("DATABASE_URL")
try:
    if database_url:
        connection = psycopg.connect(database_url)
    else:
        connection = psycopg.connect(
            dbname=os.environ["POSTGRES_DB"],
            user=(
                os.environ.get("POSTGRES_APPLICATION_USER")
                or os.environ["POSTGRES_USER"]
            ),
            password=(
                os.environ.get("POSTGRES_APPLICATION_PASSWORD")
                or os.environ["POSTGRES_PASSWORD"]
            ),
            host=os.environ["POSTGRES_HOST"],
            port=os.environ.get("POSTGRES_PORT", "5432"),
        )
    connection.close()
except psycopg.OperationalError:
    sys.exit(1)
sys.exit(0)
PY
}

wait_timeout="${DB_WAIT_TIMEOUT:-60}"
wait_interval="${DB_WAIT_INTERVAL:-1}"
wait_started_at=$(date +%s)

until postgres_ready; do
  if [ "$(( $(date +%s) - wait_started_at ))" -ge "$wait_timeout" ]; then
    echo "PostgreSQL did not become available within ${wait_timeout}s." >&2
    exit 1
  fi
  echo "Waiting for PostgreSQL to become available…" >&2
  sleep "$wait_interval"
done

echo "PostgreSQL is available." >&2

exec .venv/bin/gunicorn \
  config.asgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --control-socket /tmp/gunicorn.ctl \
  --workers "${GUNICORN_WORKERS:-2}" \
  --worker-class uvicorn_worker.UvicornWorker \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --access-logfile - \
  --error-logfile -
