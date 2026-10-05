#!/usr/bin/env bash
# Start the VANTA API (:8811) and web UI (:5173) in the background.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
setsid nohup .venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8811 > server.log 2>&1 < /dev/null &
cd "$ROOT/frontend"
setsid nohup npm run dev -- --host 127.0.0.1 --port 5173 > vite.log 2>&1 < /dev/null &
echo "api :8811, web :5173"
