#!/usr/bin/env bash
# Stage the upload-url Lambda (code + Linux x86_64 deps + RDS CA bundle) into
# app/lambdas/upload_url/.build. Terraform zips that directory, so run this before plan/apply.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/../app/lambdas/upload_url" && pwd)"
OUT="$SRC/.build"

rm -rf "$OUT"
mkdir -p "$OUT"

uv pip install --quiet \
  --target "$OUT" \
  --python-version 3.12 \
  --python-platform x86_64-manylinux_2_28 \
  --only-binary :all: \
  -r "$SRC/requirements.txt"

cp "$SRC/handler.py" "$OUT/"
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o "$OUT/rds-global-bundle.pem"

# Stable mtimes so an unchanged build produces an identical zip (no needless Lambda updates).
find "$OUT" -exec touch -h -t 202001010000 {} +

echo "Built $OUT"
