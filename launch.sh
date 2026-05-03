#!/usr/bin/env bash
set -e

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR"

echo "🚀 Launching LexFlow development environment..."

echo "\n1) Preparing backend..."
cd "$WORKDIR/backend"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -d "$WORKDIR/frontend/node_modules" ]; then
  echo "\n2) Installing frontend dependencies..."
  cd "$WORKDIR/frontend"
  npm install
fi

BACKEND_LOG="$WORKDIR/backend.log"
FRONTEND_LOG="$WORKDIR/frontend.log"

cd "$WORKDIR/backend"
echo "\n3) Starting backend on http://localhost:10000"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 10000 --reload >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cd "$WORKDIR/frontend"
echo "4) Starting frontend on http://localhost:5173"
npm run dev >"$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

echo "\nBackend log: $BACKEND_LOG"
echo "Frontend log: $FRONTEND_LOG"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Press Ctrl+C to stop both servers."

trap 'echo "\nStopping servers..."; kill $BACKEND_PID $FRONTEND_PID >/dev/null 2>&1; exit 0' INT TERM
wait
