#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
sha="$(git -C "$ROOT" rev-parse HEAD)"

ENV_FILE="$ROOT/frontend/.env.deploy"
if [ ! -f "$ENV_FILE" ]; then
  echo "prebuild-upload: missing $ENV_FILE" >&2
  exit 1
fi

CACHE_DIR="$HOME/.cache/tortobaza"
WORKTREE="$CACHE_DIR/build-worktree"
STAMP="$CACHE_DIR/package-lock.sha"
mkdir -p "$CACHE_DIR"

if [ -d "$WORKTREE" ]; then
  git -C "$WORKTREE" checkout --detach "$sha"
else
  git -C "$ROOT" worktree add --detach "$WORKTREE" "$sha"
fi

cp "$ENV_FILE" "$WORKTREE/frontend/.env.production.local"

lock_hash="$(shasum -a 256 "$WORKTREE/frontend/package-lock.json" | awk '{print $1}')"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$lock_hash" ]; then
  npm ci --prefix "$WORKTREE/frontend"
  printf '%s\n' "$lock_hash" > "$STAMP"
fi

cd "$WORKTREE/frontend"
SKIP_TYPECHECK=1 npm run build

stage="$(mktemp -d)"
zip -qr "$stage/$sha.zip" .next -x '.next/cache/*'
scp "$stage/$sha.zip" "aws:/data/tortobaza_builds/$sha.zip.tmp"
ssh aws mv "/data/tortobaza_builds/$sha.zip.tmp" "/data/tortobaza_builds/$sha.zip"
rm -rf "$stage"
