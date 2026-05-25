#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUILD_DIR=".next-new"
LIVE_DIR=".next"
BACKUP_DIR=".next-old"

export NEXT_DIST_DIR="$BUILD_DIR"
npm run build

rm -rf "$BACKUP_DIR"
if [ -d "$LIVE_DIR" ]; then
  mv "$LIVE_DIR" "$BACKUP_DIR"
fi
mv "$BUILD_DIR" "$LIVE_DIR"
rm -rf "$BACKUP_DIR"
