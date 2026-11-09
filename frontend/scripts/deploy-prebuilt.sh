#!/usr/bin/env bash
set -euo pipefail

archive="$1"
cd "$(dirname "$0")/.."

rm -rf .next-new .next-unpack
mkdir -p .next-unpack
unzip -q "$archive" -d .next-unpack
mv .next-unpack/.next .next-new
rm -rf .next-unpack

rm -rf .next-old
if [ -d .next ]; then
  mv .next .next-old
fi
mv .next-new .next
rm -rf .next-old
