#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8000}"

if ! pids="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null)" || [ -z "$pids" ]; then
  echo "No listening process found on port $PORT."
  exit 0
fi

echo "Stopping process on port $PORT:"
ps -o pid=,ppid=,stat=,command= -p $pids

kill $pids
sleep 1

if pids_after="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null)" && [ -n "$pids_after" ]; then
  echo
  echo "Process still holds port $PORT. Force kill with:"
  echo "  kill -9 $pids_after"
  exit 1
fi

echo "Port $PORT is free."
