#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "====================================="
echo "  AI-EFSV Launcher"
echo "====================================="

# --- Chronos anomaly service (C3a) ---
if [ -d "$SCRIPT_DIR/backend/chronos_service/.venv" ]; then
  echo "[1/4] Starting Chronos anomaly service..."
  osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/backend/chronos_service' && source .venv/bin/activate && uvicorn app:app --host 127.0.0.1 --port 9001\""
  sleep 3
else
  echo "[1/4] Chronos service skipped (no .venv found — see backend/chronos_service/README.md to set it up)"
fi

# --- Backend ---
echo "[2/4] Starting backend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/backend' && source .venv/bin/activate && python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000\""

sleep 3

# --- Frontend ---
echo "[3/4] Starting frontend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/frontend' && npm run dev\""

sleep 3

# --- ngrok ---
echo "[4/4] Starting ngrok..."
osascript -e "tell application \"Terminal\" to do script \"ngrok http --url=active-mustard-chemicals.ngrok-free.dev 5173\""

echo ""
echo "====================================="
echo "  Public URL: https://active-mustard-chemicals.ngrok-free.dev"
echo "====================================="
open "https://active-mustard-chemicals.ngrok-free.dev"
