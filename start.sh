#!/usr/bin/env bash
# Starts the ProspectorBot API and web interface together. Ctrl+C stops both.
set -euo pipefail
cd "$(dirname "$0")"

API_URL=http://127.0.0.1:8000
WEB_URL=http://localhost:3000

port_in_use() { (echo >"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
for port in 8000 3000; do
  if port_in_use "$port"; then
    echo "Port $port is already in use; stop whatever is running there first." >&2
    exit 1
  fi
done

# Install or refresh dependencies only when they are missing or out of date.
if [[ ! -x .venv/bin/python ]]; then
  echo "→ Creating Python environment"
  python3 -m venv .venv
fi
if [[ ! -f .venv/.installed || pyproject.toml -nt .venv/.installed ]]; then
  echo "→ Installing backend dependencies"
  .venv/bin/pip install --quiet -e . && touch .venv/.installed
fi
if [[ ! -f frontend/node_modules/.package-lock.json || frontend/package-lock.json -nt frontend/node_modules/.package-lock.json ]]; then
  echo "→ Installing frontend dependencies"
  (cd frontend && npm install --no-audit --no-fund)
fi
[[ -f frontend/.env.local ]] || cp frontend/.env.example frontend/.env.local
[[ -f .env ]] || echo "Warning: no .env found; prospecting needs GEOAPIFY_API_KEY (see .env.example)." >&2

# Each service runs in its own session so stopping it also stops its children (e.g. next dev).
pids=()
start() {
  local name=$1; shift
  setsid "$@" > >(sed -u "s/^/[$name] /") 2>&1 &
  pids+=("$!")
}
stop() {
  trap - INT TERM EXIT
  echo
  echo "Stopping ProspectorBot…"
  for pid in "${pids[@]}"; do kill -- "-$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop INT TERM EXIT

start api .venv/bin/prospector serve
start web npm --prefix frontend run dev -- --port 3000

for _ in $(seq 60); do
  if curl -sf "$API_URL/api/health" >/dev/null && curl -sf -o /dev/null "$WEB_URL"; then
    echo
    echo "  ProspectorBot is running → $WEB_URL   (Ctrl+C to stop)"
    echo
    break
  fi
  sleep 1
done

# If either service exits on its own, stop the other one too.
wait -n "${pids[@]}" || true
