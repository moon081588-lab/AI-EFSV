#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "====================================="
echo "  AI-EFSV Launcher"
echo "====================================="

# --- Backend ---
echo "[1/3] Starting backend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/backend' && source .venv/bin/activate && python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000\""

sleep 3

# --- Frontend ---
echo "[2/3] Starting frontend..."
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR/frontend' && npm run dev\""

sleep 3

# --- ngrok ---
echo "[3/3] Starting ngrok..."
osascript -e "tell application \"Terminal\" to do script \"ngrok http --url=active-mustard-chemicals.ngrok-free.dev 5173\""

echo ""
echo "====================================="
echo "  Public URL: https://active-mustard-chemicals.ngrok-free.dev"
echo "====================================="
open "https://active-mustard-chemicals.ngrok-free.dev"
