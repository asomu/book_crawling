#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
PORT="${PORT:-8000}"

if [ ! -d ".venv" ]; then
  echo ".venv is missing. Run ./scripts/bootstrap.sh first."
  exit 1
fi

. .venv/bin/activate

if pids="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null)" && [ -n "$pids" ]; then
  echo "Port $PORT is already in use."
  echo "Listening process:"
  ps -o pid=,ppid=,stat=,command= -p $pids
  echo
  echo "If this is an old dev server, stop it first:"
  echo "  ./scripts/stop.sh"
  echo "or force kill the PID:"
  echo "  kill -9 $pids"
  echo
  echo "To run on a different port:"
  echo "  PORT=8001 ./scripts/dev.sh"
  exit 1
fi

exec uvicorn app.main:app --reload --port "$PORT"
