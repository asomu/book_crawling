#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv is missing. Run ./scripts/bootstrap.sh first."
  exit 1
fi

. .venv/bin/activate
python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/")
    print("status:", response.status_code)
    print("contains_title:", "Book Crawling 후딱 v2" in response.text)
PY
