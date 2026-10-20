#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/koding/tortobaza
STATUS_DIR=/home/ubuntu/.tortobaza
STATUS="$STATUS_DIR/deploy.json"
LOCK="$STATUS_DIR/deploy.lock"

mkdir -p "$STATUS_DIR"
exec 9>"$LOCK"
flock 9

cd "$ROOT"

ATTEMPTED=""

write_status() {
  local status="$1"
  local attempted="$2"
  local error="$3"
  local now
  now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  STATUS_PATH="$STATUS" STATUS_STATE="$status" ATTEMPTED_SHA="$attempted" ERROR_TEXT="$error" NOW="$now" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["STATUS_PATH"])
data = {}
if path.exists():
    data = json.loads(path.read_text())
status = os.environ["STATUS_STATE"]
attempted = os.environ["ATTEMPTED_SHA"]
now = os.environ["NOW"]
data["attempted_sha"] = attempted
data["status"] = status
if status == "running":
    data["started_at"] = now
    data["finished_at"] = None
    data["error"] = None
elif status == "success":
    data["sha"] = attempted
    data["finished_at"] = now
    data["error"] = None
elif status == "failed":
    data["finished_at"] = now
    data["error"] = os.environ["ERROR_TEXT"]
else:
    raise SystemExit(f"unknown status {status}")
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n")
tmp.replace(path)
PY
}

on_err() {
  local code=$?
  trap - ERR
  if [ -n "$ATTEMPTED" ]; then
    write_status failed "$ATTEMPTED" "command failed (exit ${code}): ${BASH_COMMAND}"
  fi
  exit "$code"
}
trap on_err ERR

success_sha() {
  python3 - "$STATUS" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
data = json.loads(path.read_text())
if "sha" not in data:
    raise SystemExit(1)
print(data["sha"])
PY
}

target=""
while true; do
  git fetch origin master >&2
  target=$(git rev-parse origin/master)
  current=""
  if current=$(success_sha); then
    :
  else
    current=""
  fi
  if [ -n "$current" ] && [ "$current" = "$target" ]; then
    break
  fi
  ATTEMPTED=$target
  write_status running "$target" ""
  git checkout master >&2
  git merge --ff-only "$target" >&2
  "$ROOT/backend/deploy.sh" >&2
  "$ROOT/frontend/deploy.sh" >&2
  write_status success "$target" ""
done

echo "$target"
