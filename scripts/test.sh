#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo ".venv is missing. Run ./scripts/bootstrap.sh first."
  exit 1
fi

. .venv/bin/activate
exec pytest
