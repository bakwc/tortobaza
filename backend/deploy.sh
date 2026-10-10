#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

git pull --ff-only
poetry install --no-root
poetry run python manage.py migrate

for port in 8101 8102; do
  sudo systemctl restart "tortobaza-backend@${port}"
  sleep 1
  timeout 60 bash -c "until curl -sf http://127.0.0.1:${port}/health/ >/dev/null; do sleep 1; done"
done
