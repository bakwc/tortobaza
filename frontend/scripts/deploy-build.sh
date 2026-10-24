#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BUILD_DIR=".next-new"
LIVE_DIR=".next"
BACKUP_DIR=".next-old"
CACHE_DIR=".next-cache"

copy_cache() {
  local src="$1"
  local dest="$2"
  local entry name
  rm -rf "$dest"
  mkdir -p "$dest"
  shopt -s nullglob
  for entry in "$src"/*; do
    name=$(basename "$entry")
    if [ "$name" = "images" ]; then
      continue
    fi
    cp -a "$entry" "$dest/$name"
  done
  shopt -u nullglob
}

if [ -d "$CACHE_DIR" ]; then
  copy_cache "$CACHE_DIR" "$BUILD_DIR/cache"
elif [ -d "$LIVE_DIR/cache" ]; then
  copy_cache "$LIVE_DIR/cache" "$BUILD_DIR/cache"
fi

export NEXT_DIST_DIR="$BUILD_DIR"
npm run build

copy_cache "$BUILD_DIR/cache" "$CACHE_DIR"

rm -rf "$BACKUP_DIR"
if [ -d "$LIVE_DIR" ]; then
  mv "$LIVE_DIR" "$BACKUP_DIR"
fi
mv "$BUILD_DIR" "$LIVE_DIR"
rm -rf "$BACKUP_DIR"
