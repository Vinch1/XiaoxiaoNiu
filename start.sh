#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
FRONTEND_DIR="$ROOT_DIR/Frontend"

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "${BACKEND_PID:-}" ] && kill "$BACKEND_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}

run_frontend_build() {
    echo ""
    echo "[frontend] Installing dependencies..."
    cd "$FRONTEND_DIR"

    if [ -f package-lock.json ]; then
        npm ci
    else
        npm install
    fi

    echo ""
    echo "[frontend] Building static assets..."
    npm run build
}

if [ "${VERCEL:-}" = "1" ]; then
    echo "=== XiaoxiaoNiu Vercel Build ==="
    run_frontend_build
    echo ""
    echo "Vercel build step completed."
    exit 0
fi

trap cleanup EXIT INT TERM

echo "=== XiaoxiaoNiu Server Setup ==="

# --- Backend install ---
echo ""
echo "[1/3] Installing backend dependencies..."
cd "$ROOT_DIR"
uv sync

# --- Frontend build ---
echo ""
echo "[2/3] Building frontend..."
run_frontend_build

# --- Start backend ---
echo ""
echo "[3/3] Starting server on ${HOST}:${PORT}..."
cd "$ROOT_DIR"
SERVE_FRONTEND_STATIC=1 uv run uvicorn Backend.api:app --host "$HOST" --port "$PORT" &
BACKEND_PID=$!

echo ""
echo "=== Server running ==="
echo "  http://${HOST}:${PORT}"
echo "  Press Ctrl+C to stop."
echo ""

wait
