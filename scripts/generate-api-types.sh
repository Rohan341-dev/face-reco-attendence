#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
.venv/bin/python manage.py spectacular --file "$ROOT/shared/openapi.json" --format openapi-json
cd "$ROOT/web"
mkdir -p src/lib/api/generated
npx openapi-typescript "$ROOT/shared/openapi.json" -o src/lib/api/generated/types.ts
for app in mobile terminal; do
  mkdir -p "$ROOT/$app/src/lib/api/generated"
  cp src/lib/api/generated/types.ts "$ROOT/$app/src/lib/api/generated/types.ts"
done
