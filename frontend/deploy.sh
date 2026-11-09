#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export NODE_OPTIONS="--max-old-space-size=4096"
npm ci
sha=$(git rev-parse HEAD)
archive="/data/tortobaza_builds/$sha.zip"
if [ -f "$archive" ]; then
  bash scripts/deploy-prebuilt.sh "$archive"
else
  taskset -c 0 npm run build:deploy
fi
sudo systemctl restart tortobaza-frontend
