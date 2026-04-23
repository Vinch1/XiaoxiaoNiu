#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

echo "=== XiaoxiaoNiu Server Setup ==="

# --- Backend install ---
echo ""
echo "[1/3] Installing backend dependencies..."
cd "$ROOT_DIR"
uv sync

# --- Frontend build ---
echo ""
echo "[2/3] Installing and building frontend..."
cd "$ROOT_DIR/Frontend"
npm install
npm run build

# --- Mount static files into FastAPI on first run ---
STATIC_DIR="$ROOT_DIR/Frontend/dist"
SERVE_FLAG="$ROOT_DIR/.serve_static"

if [ ! -f "$SERVE_FLAG" ]; then
    cat >> "$ROOT_DIR/Backend/api.py" <<'PYEOF'

# --- Serve frontend static files (added by start.sh) ---
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory=str(Path(__file__).resolve().parent.parent / "Frontend" / "dist"), html=True), name="static")
PYEOF
    touch "$SERVE_FLAG"
    echo "    Static file serving enabled."
fi

# --- Start backend ---
echo ""
echo "[3/3] Starting server on ${HOST}:${PORT}..."
cd "$ROOT_DIR"
uv run uvicorn Backend.api:app --host "$HOST" --port "$PORT" &
BACKEND_PID=$!

echo ""
echo "=== Server running ==="
echo "  http://${HOST}:${PORT}"
echo "  Press Ctrl+C to stop."
echo ""

wait
