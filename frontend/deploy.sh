#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

export NODE_OPTIONS="--max-old-space-size=4096"
taskset -c 0 npm run build:deploy
sudo systemctl restart tortobaza-frontend
